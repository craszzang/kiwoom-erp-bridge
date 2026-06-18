"""Host bridge: Kiwoom + scanner on main thread, HTTP/WS in background threads."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import queue
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from PyQt5.QtCore import QTimer

from auto_trader.bridge_protocol import (
    BRIDGE_VERSION,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_HTTP_PORT,
    SYNC_EXCLUDE,
    SYNC_GLOBS,
)
from auto_trader.condition_picker import ConditionChoice
from auto_trader.config import TraderConfig
from auto_trader.kiwoom_api import KiwoomAPI
from auto_trader.stock_scanner import ConditionStockScanner, StockQuote

logger = logging.getLogger(__name__)


def _quote_to_dict(q: StockQuote) -> dict[str, Any]:
    return {
        "code": q.code,
        "name": q.name,
        "price": q.price,
        "change_amount": q.change_amount,
        "change_pct": q.change_pct,
        "sell_total": q.sell_total,
        "buy_total": q.buy_total,
        "execution_strength": q.execution_strength,
    }


def _build_sync_manifest(root: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    bundle = hashlib.sha256()
    for pattern in SYNC_GLOBS:
        for path in sorted(root.glob(pattern)):
            rel = path.relative_to(root).as_posix()
            if rel in SYNC_EXCLUDE:
                continue
            if not path.is_file():
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            bundle.update(rel.encode("utf-8"))
            bundle.update(digest.encode("ascii"))
            files[rel] = {
                "sha256": digest,
                "size": len(data),
                "mtime": int(path.stat().st_mtime),
            }
    return {
        "bridge_version": BRIDGE_VERSION,
        "bundle_version": bundle.hexdigest()[:12],
        "files": files,
    }


class BridgeController:
    def __init__(self, api: KiwoomAPI, config: TraderConfig, root: Path) -> None:
        self.api = api
        self.config = config
        self.root = root
        self.scanner: ConditionStockScanner | None = None
        self._token = str(getattr(config, "bridge_token", "") or "")
        self._cmd_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._ws_clients: set[Any] = set()
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._pending_delta: dict[str, dict[str, Any]] = {}
        self._last_broadcast = 0.0
        self._http_server: ThreadingHTTPServer | None = None
        self._ws_thread: threading.Thread | None = None
        self._selected_conditions: list[ConditionChoice] = []

    def start(self, ws_port: int = DEFAULT_BRIDGE_PORT, http_port: int = DEFAULT_HTTP_PORT) -> None:
        self._start_http(http_port)
        self._start_ws(ws_port)
        QTimer.singleShot(50, self._poll_commands)

    def attach_scanner(self, scanner: ConditionStockScanner) -> None:
        self.scanner = scanner
        scanner.on_state_change = self._on_scanner_change

    def status_payload(self) -> dict[str, Any]:
        return {
            "bridge_version": BRIDGE_VERSION,
            "kiwoom_connected": self.api.is_connected(),
            "accounts": self.api.get_accounts() if self.api.is_connected() else [],
            "server_gubun": self.api.get_login_info("GetServerGubun") if self.api.is_connected() else "",
            "scanner_ready": self.scanner is not None,
            "last_condition_count": self.scanner.last_condition_count if self.scanner else 0,
        }

    def scanner_meta(self) -> dict[str, Any]:
        if not self.scanner:
            return {}
        return {
            "last_condition_count": self.scanner.last_condition_count,
            "market_mode": self.scanner.market_mode,
            "lite_rows": self.scanner.lite_rows,
            "condition_codes": list(self.scanner.condition_codes[:500]),
        }

    def quotes_payload(self, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.scanner:
            return []
        rows = list(self.scanner.quotes.values())
        if limit is not None:
            rows = rows[:limit]
        return [_quote_to_dict(q) for q in rows]

    def _on_scanner_change(self) -> None:
        if not self.scanner:
            return
        for code, q in self.scanner.quotes.items():
            self._pending_delta[code] = _quote_to_dict(q)
        QTimer.singleShot(0, self._flush_ws_delta)

    def _flush_ws_delta(self) -> None:
        if not self._pending_delta or not self._ws_loop:
            return
        batch = list(self._pending_delta.values())
        self._pending_delta.clear()
        if len(batch) > 400:
            self._broadcast({"type": "quotes_snapshot", "data": batch})
        else:
            self._broadcast({"type": "quotes_delta", "data": batch})

    def _broadcast(self, msg: dict[str, Any]) -> None:
        if not self._ws_loop or not self._ws_clients:
            return
        raw = json.dumps(msg, ensure_ascii=False)

        async def _send() -> None:
            dead = []
            for ws in list(self._ws_clients):
                try:
                    await ws.send(raw)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._ws_clients.discard(ws)

        asyncio.run_coroutine_threadsafe(_send(), self._ws_loop)

    def _poll_commands(self) -> None:
        while True:
            try:
                cmd = self._cmd_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_command(cmd)
        QTimer.singleShot(50, self._poll_commands)

    def _handle_command(self, cmd: dict[str, Any]) -> None:
        action = cmd.get("action")
        if action == "bootstrap":
            self._cmd_bootstrap(cmd)
        elif action == "refresh":
            self._cmd_refresh(cmd)
        elif action == "order":
            self._cmd_order(cmd)

    def _cmd_bootstrap(self, cmd: dict[str, Any]) -> None:
        if not self.scanner:
            return
        filters = cmd.get("filters") or {}
        if "min_sell_balance_pct" in filters:
            self.config.min_sell_balance_pct = float(filters["min_sell_balance_pct"])
        if "min_execution_strength" in filters:
            self.config.min_execution_strength = float(filters["min_execution_strength"])
        if "filter_pass_only" in filters:
            self.config.filter_pass_only = bool(filters["filter_pass_only"])
        if cmd.get("watch_mode"):
            self.config.watch_mode = str(cmd["watch_mode"])

        conds = [
            ConditionChoice(index=int(c["index"]), name=str(c["name"]))
            for c in (cmd.get("conditions") or [])
        ]
        self._selected_conditions = conds
        self.scanner.bootstrap(conditions=conds)
        cmd["result"] = {
            "meta": self.scanner_meta(),
            "quotes": self.quotes_payload(limit=5000),
        }
        self._broadcast({"type": "scanner_meta", "data": self.scanner_meta()})
        self._broadcast({"type": "quotes_snapshot", "data": cmd["result"]["quotes"]})

    def _cmd_refresh(self, cmd: dict[str, Any]) -> None:
        if not self.scanner:
            cmd["result"] = {"added": 0}
            return
        added = self.scanner.refresh_condition_snapshot()
        cmd["result"] = {
            "added": added,
            "meta": self.scanner_meta(),
            "quotes": self.quotes_payload(limit=5000) if added else [],
        }

    def _cmd_order(self, cmd: dict[str, Any]) -> None:
        body = cmd.get("body") or {}
        ret = self.api.send_order(
            rq_name=str(body.get("rq_name", "")),
            screen_no=str(body.get("screen_no", self.config.screen_no)),
            acc_no=str(body.get("acc_no", "")),
            order_type=int(body.get("order_type", 1)),
            code=str(body.get("code", "")),
            qty=int(body.get("qty", 0)),
            price=int(body.get("price", 0)),
            hoga_gb=str(body.get("hoga_gb", "03")),
            org_order_no=str(body.get("org_order_no", "")),
        )
        cmd["result"] = {"ret": ret}

    def on_chejan(self, gubun: str, item_cnt: int, fid_list: str) -> None:
        fids = {
            9001: self.api.get_chejan_data(9001),
            910: self.api.get_chejan_data(910),
            911: self.api.get_chejan_data(911),
            905: self.api.get_chejan_data(905),
            302: self.api.get_chejan_data(302),
            913: self.api.get_chejan_data(913),
        }
        self._broadcast(
            {
                "type": "chejan",
                "data": {
                    "gubun": gubun,
                    "item_cnt": item_cnt,
                    "fid_list": fid_list,
                    "fids": fids,
                },
            }
        )

    def _check_token(self, handler: BaseHTTPRequestHandler) -> bool:
        if not self._token:
            return True
        return handler.headers.get("X-Bridge-Token", "") == self._token

    def _start_http(self, port: int) -> None:
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                logger.debug(format, *args)

            def _json_response(self, code: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    return {}
                body = self.rfile.read(length)
                return json.loads(body.decode("utf-8"))

            def do_GET(self) -> None:
                if not bridge._check_token(self):
                    self._json_response(403, {"error": "forbidden"})
                    return
                path = urlparse(self.path).path
                if path == "/api/health":
                    self._json_response(200, bridge.status_payload())
                    return
                if path == "/api/status":
                    self._json_response(200, bridge.status_payload())
                    return
                if path == "/api/sync/manifest":
                    self._json_response(200, _build_sync_manifest(bridge.root))
                    return
                if path == "/api/sync/file":
                    qs = parse_qs(urlparse(self.path).query)
                    rel = (qs.get("path") or [""])[0]
                    file_path = (bridge.root / rel).resolve()
                    if not str(file_path).startswith(str(bridge.root.resolve())):
                        self._json_response(403, {"error": "invalid path"})
                        return
                    if not file_path.is_file():
                        self._json_response(404, {"error": "not found"})
                        return
                    data = file_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if path == "/api/conditions":
                    items = []
                    if bridge.api.is_connected():
                        for idx, name in bridge.api.get_condition_name_list():
                            items.append({"index": idx, "name": name})
                    self._json_response(200, {"items": items})
                    return
                self._json_response(404, {"error": "not found"})

            def do_POST(self) -> None:
                if not bridge._check_token(self):
                    self._json_response(403, {"error": "forbidden"})
                    return
                path = urlparse(self.path).path
                body = self._read_json()
                if path == "/api/bootstrap":
                    cmd = {"action": "bootstrap", **body}
                    bridge._cmd_queue.put(cmd)
                    bridge._wait_cmd(cmd, timeout=180.0)
                    self._json_response(200, cmd.get("result") or {})
                    return
                if path == "/api/scanner/refresh":
                    cmd = {"action": "refresh"}
                    bridge._cmd_queue.put(cmd)
                    bridge._wait_cmd(cmd, timeout=90.0)
                    self._json_response(200, cmd.get("result") or {})
                    return
                if path == "/api/order":
                    cmd = {"action": "order", "body": body}
                    bridge._cmd_queue.put(cmd)
                    bridge._wait_cmd(cmd, timeout=30.0)
                    self._json_response(200, cmd.get("result") or {})
                    return
                self._json_response(404, {"error": "not found"})

        self._http_server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        threading.Thread(target=self._http_server.serve_forever, daemon=True).start()
        logger.info("HTTP bridge on 0.0.0.0:%d", port)

    def _wait_cmd(self, cmd: dict[str, Any], timeout: float) -> None:
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            if "result" in cmd:
                return
            time.sleep(0.05)

    def _start_ws(self, port: int) -> None:
        bridge = self

        def run() -> None:
            import websockets

            async def handler(ws: Any) -> None:
                if bridge._token:
                    # websockets 12+: headers on ws.request
                    hdrs = getattr(ws, "request_headers", None) or getattr(ws, "request", None)
                    token = ""
                    if hdrs is not None:
                        token = hdrs.headers.get("X-Bridge-Token", "") if hasattr(hdrs, "headers") else ""
                    if token != bridge._token:
                        await ws.close(1008, "forbidden")
                        return
                bridge._ws_clients.add(ws)
                try:
                    welcome = {
                        "type": "welcome",
                        "data": bridge.status_payload(),
                    }
                    await ws.send(json.dumps(welcome, ensure_ascii=False))
                    if bridge.scanner:
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "scanner_meta",
                                    "data": bridge.scanner_meta(),
                                },
                                ensure_ascii=False,
                            )
                        )
                    async for _ in ws:
                        pass
                finally:
                    bridge._ws_clients.discard(ws)

            async def main() -> None:
                bridge._ws_loop = asyncio.get_running_loop()
                async with websockets.serve(handler, "0.0.0.0", port, ping_interval=20):
                    await asyncio.Future()

            asyncio.run(main())

        self._ws_thread = threading.Thread(target=run, daemon=True)
        self._ws_thread.start()
        logger.info("WS bridge on 0.0.0.0:%d", port)
