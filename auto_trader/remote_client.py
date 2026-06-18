"""Remote bridge client: HTTP commands + WebSocket quote stream."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable, Callable

import requests
from PyQt5.QtCore import QObject, Qt, QTimer, pyqtSignal

from auto_trader.condition_picker import ConditionChoice
from auto_trader.config import TraderConfig
from auto_trader.remote_scanner import RemoteStockScanner

from auto_trader import i18n_ko as T

logger = logging.getLogger(__name__)


class RemoteKiwoomFacade:
    """KiwoomAPI subset used by excel_ui on remote client."""

    def __init__(self, bridge: "RemoteBridgeClient") -> None:
        self._bridge = bridge
        self._chejan_cb: Callable[[str, int, str], None] | None = None
        self._chejan_cache: dict[int, str] = {}

    def comm_connect(self, block: bool = True) -> int:
        return 0 if self._bridge.wait_host_ready() else -1

    def is_connected(self) -> bool:
        return self._bridge.host_ready

    def get_login_info(self, tag: str) -> str:
        return str(self._bridge.status.get("server_gubun", "") if tag == "GetServerGubun" else "")

    def get_accounts(self) -> list[str]:
        acc = self._bridge.status.get("accounts") or []
        return [str(a) for a in acc]

    def get_condition_name_list(self) -> list[tuple[int, str]]:
        return [(c.index, c.name) for c in self._bridge.fetch_conditions()]

    def send_order(
        self,
        rq_name: str,
        screen_no: str,
        acc_no: str,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        hoga_gb: str,
        org_order_no: str = "",
    ) -> int:
        return self._bridge.send_order(
            rq_name=rq_name,
            screen_no=screen_no,
            acc_no=acc_no,
            order_type=order_type,
            code=code,
            qty=qty,
            price=price,
            hoga_gb=hoga_gb,
            org_order_no=org_order_no,
        )

    def register_chejan_callback(self, callback: Callable[[str, int, str], None] | None) -> None:
        self._chejan_cb = callback

    def get_chejan_data(self, fid: int) -> str:
        return self._chejan_cache.get(fid, "")

    def show_account_password_window(self) -> None:
        pass

    def _on_chejan_event(self, payload: dict) -> None:
        fids = payload.get("fids") or {}
        self._chejan_cache = {int(k): str(v) for k, v in fids.items()}
        if self._chejan_cb is not None:
            self._chejan_cb(
                str(payload.get("gubun", "0")),
                int(payload.get("item_cnt", 0)),
                str(payload.get("fid_list", "")),
            )


class _WsSignals(QObject):
    payload = pyqtSignal(dict)


class RemoteBridgeClient:
    def __init__(self, host: str, port: int, token: str = "", http_port: int | None = None) -> None:
        self.host = host.strip()
        self.port = int(port)
        self.http_port = int(http_port or (self.port + 1))
        self.token = token.strip()
        self.status: dict[str, Any] = {}
        self.host_ready = False
        self.scanner: RemoteStockScanner | None = None
        self._signals = _WsSignals()
        self._signals.payload.connect(self._dispatch_ws, Qt.QueuedConnection)
        self._ws_thread: threading.Thread | None = None
        self._ws_stop = threading.Event()
        self._api_facade: RemoteKiwoomFacade | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    def _headers(self) -> dict[str, str]:
        return {"X-Bridge-Token": self.token} if self.token else {}

    def connect(
        self,
        *,
        timeout_sec: float = 30.0,
        on_tick: Callable[[str], None] | None = None,
    ) -> bool:
        if not self.wait_host_ready(timeout_sec=timeout_sec, on_tick=on_tick):
            return False
        self._start_ws()
        return True

    def create_api(self) -> RemoteKiwoomFacade:
        if self._api_facade is None:
            self._api_facade = RemoteKiwoomFacade(self)
        return self._api_facade

    def attach_scanner(self, config: TraderConfig) -> RemoteStockScanner:
        self.scanner = RemoteStockScanner(config=config)
        return self.scanner

    def wait_host_ready(
        self,
        timeout_sec: float = 30.0,
        on_tick: Callable[[str], None] | None = None,
    ) -> bool:
        import time

        deadline = time.time() + timeout_sec
        host_seen = False
        while time.time() < deadline:
            try:
                resp = requests.get(
                    f"{self.base_url}/api/status",
                    headers=self._headers(),
                    timeout=3,
                )
                resp.raise_for_status()
                self.status = resp.json()
                host_seen = True
                if self.status.get("kiwoom_connected"):
                    self.host_ready = True
                    if on_tick:
                        on_tick(T.BRIDGE_TICK_KIWOOM_OK)
                    return True
                if on_tick:
                    on_tick(
                        T.BRIDGE_TICK_HOST_OK.format(host=self.host, port=self.http_port)
                    )
            except Exception:
                if on_tick:
                    on_tick(T.BRIDGE_TICK_CONNECTING.format(host=self.host))
            time.sleep(0.5)
        self.host_ready = False
        if host_seen and on_tick:
            on_tick(T.BRIDGE_TICK_NO_KIWOOM)
        return False

    def fetch_conditions(self) -> list[ConditionChoice]:
        resp = requests.get(
            f"{self.base_url}/api/conditions",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [ConditionChoice(index=int(c["index"]), name=str(c["name"])) for c in data.get("items", [])]

    def bootstrap(self, conditions: list[ConditionChoice], config: TraderConfig) -> None:
        body = {
            "conditions": [{"index": c.index, "name": c.name} for c in conditions],
            "filters": {
                "min_sell_balance_pct": config.min_sell_balance_pct,
                "min_execution_strength": config.min_execution_strength,
                "filter_pass_only": config.filter_pass_only,
            },
            "watch_mode": config.watch_mode,
        }
        resp = requests.post(
            f"{self.base_url}/api/bootstrap",
            headers=self._headers(),
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()
        if self.scanner:
            self.scanner.apply_meta(payload.get("meta") or {})
            self.scanner.apply_snapshot(payload.get("quotes") or [])

    def refresh_snapshot(self) -> int:
        resp = requests.post(
            f"{self.base_url}/api/scanner/refresh",
            headers=self._headers(),
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        added = int(payload.get("added", 0))
        if self.scanner:
            self.scanner.apply_meta(payload.get("meta") or {})
            if payload.get("quotes"):
                self.scanner.apply_snapshot(payload["quotes"])
        return added

    def send_order(self, **kwargs: Any) -> int:
        resp = requests.post(
            f"{self.base_url}/api/order",
            headers=self._headers(),
            json=kwargs,
            timeout=15,
        )
        resp.raise_for_status()
        return int(resp.json().get("ret", -1))

    def _start_ws(self) -> None:
        if self._ws_thread and self._ws_thread.is_alive():
            return
        self._ws_stop.clear()
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

    def _ws_loop(self) -> None:
        try:
            import asyncio
            import websockets
        except ImportError:
            logger.error("websockets package required on client")
            return

        uri = f"ws://{self.host}:{self.port}/ws"

        def _open_ws():
            kwargs: dict[str, Any] = {"ping_interval": 20, "open_timeout": 10}
            if self.token:
                headers = {"X-Bridge-Token": self.token}
                for key in ("additional_headers", "extra_headers"):
                    try:
                        return websockets.connect(uri, **kwargs, **{key: headers})
                    except TypeError:
                        continue
            return websockets.connect(uri, **kwargs)

        async def run() -> None:
            while not self._ws_stop.is_set():
                try:
                    async with _open_ws() as ws:
                        async for raw in ws:
                            if self._ws_stop.is_set():
                                break
                            try:
                                msg = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            self._signals.payload.emit(msg)
                except Exception as exc:
                    logger.warning("ws reconnect: %s", exc)
                    await asyncio.sleep(2.0)

        asyncio.run(run())

    def _dispatch_ws(self, msg: dict) -> None:
        kind = msg.get("type")
        if kind == "quotes_snapshot" and self.scanner:
            self.scanner.apply_snapshot(msg.get("data") or [])
        elif kind == "quotes_delta" and self.scanner:
            self.scanner.apply_delta(msg.get("data") or [])
        elif kind == "scanner_meta" and self.scanner:
            self.scanner.apply_meta(msg.get("data") or {})
        elif kind == "chejan" and self._api_facade:
            self._api_facade._on_chejan_event(msg.get("data") or {})

    def close(self) -> None:
        self._ws_stop.set()
