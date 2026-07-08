"""Parallel paper trading — one DailyEngine per condition lane."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from PyQt5.QtCore import QTimer

from auto_trader.daily_engine import DailyEngine
from auto_trader.lane_version import LaneVersion
from auto_trader.minute_bars import MinuteBarLoader

if TYPE_CHECKING:
    from auto_trader.config import TraderConfig
    from auto_trader.kiwoom_api import KiwoomAPI
    from auto_trader.stock_scanner import ConditionStockScanner

logger = logging.getLogger(__name__)


@dataclass
class _LaneState:
    version: LaneVersion
    engine: DailyEngine


class ParallelDailyRunner:
    """Run multiple condition lanes in parallel on one Kiwoom connection."""

    def __init__(
        self,
        api: "KiwoomAPI",
        config: "TraderConfig",
        scanner: "ConditionStockScanner",
        lanes: list[LaneVersion],
        on_update: Callable[[], None] | None = None,
    ) -> None:
        self.api = api
        self.config = config
        self.scanner = scanner
        self._on_update = on_update
        self._loader = MinuteBarLoader(api, getattr(config, "brm_tr_screen_no", "0104"), bar_minutes=1)
        self._lanes: list[_LaneState] = []
        for lv in lanes:
            params = lv.daily_params()
            engine = DailyEngine(
                params,
                lane_version_id=lv.version_id,
                condition_name=lv.condition_name,
            )
            self._lanes.append(_LaneState(version=lv, engine=engine))
        self._active = False
        self._tick = QTimer()
        self._tick.setInterval(600)
        self._tick.timeout.connect(self._on_tick)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def lanes(self) -> list[_LaneState]:
        return list(self._lanes)

    @property
    def engine(self) -> DailyEngine | None:
        if not self._lanes:
            return None
        return self._lanes[0].engine

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        all_codes: list[str] = []
        for st in self._lanes:
            codes = self._codes_for_lane(st.version.condition_name)
            all_codes.extend(codes)
            logger.info(
                "lane %s %s symbols=%d",
                st.version.condition_name,
                st.version.version_id,
                len(codes),
            )
        uniq = list(dict.fromkeys(all_codes))
        self._loader.enqueue(uniq[:80])
        ms = min((st.engine.params.tick_ms for st in self._lanes), default=600)
        self._tick.setInterval(max(300, ms))
        self._tick.start()
        logger.info("ParallelDailyRunner start lanes=%d", len(self._lanes))

    def stop(self) -> None:
        self._active = False
        self._tick.stop()

    def _codes_for_lane(self, condition_name: str) -> list[str]:
        codes = self.scanner.codes_for_condition(condition_name)
        if codes:
            return codes[:40]
        if self.scanner.quotes:
            return list(self.scanner.quotes.keys())[:40]
        return list(self.scanner.condition_codes)[:40]

    def _on_tick(self) -> None:
        if not self._active:
            return
        now = datetime.now()
        for st in self._lanes:
            params = st.engine.params
            for code in self._codes_for_lane(st.version.condition_name)[: params.max_symbols]:
                q = self.scanner.quotes.get(code)
                if not q or q.price <= 0:
                    continue
                store = self._loader.store(code)
                if q.cum_volume:
                    store.update_cum_volume(int(q.cum_volume), now)
                store.update_tick(float(q.price), now)
                sig = st.engine.evaluate(
                    code,
                    q.name or code,
                    float(q.price),
                    q.sell_balance_pct,
                    q.execution_strength,
                    q.sell_total,
                    q.buy_total,
                    now,
                    store,
                )
                if sig.action.value != "NONE":
                    if not params.paper_only:
                        self._send_order(sig)
                    st.engine.apply_signal(sig, now)
        if self._on_update:
            self._on_update()

    def _send_order(self, sig) -> None:
        acc = self.config.active_account_no or self.config.account_no
        if not acc:
            return
        is_buy = sig.action.value == "BUY"
        self.api.send_order(
            rq_name="daily_buy" if is_buy else "daily_sell",
            screen_no=self.config.screen_no,
            acc_no=acc,
            order_type=1 if is_buy else 2,
            code=sig.code,
            qty=sig.qty,
            price=0,
            hoga_gb="03",
        )

    def status_text(self) -> str:
        parts: list[str] = []
        for st in self._lanes:
            s = st.engine.book.stats
            parts.append(
                f"{st.version.condition_name[:6]}({st.version.version_id}):"
                f"{s.realized_pnl:+,.0f} 보유{len(st.engine.book.positions)}"
            )
        return "병렬 | " + " · ".join(parts[:6])

    def all_lane_books(self) -> list[tuple[LaneVersion, object]]:
        return [(st.version, st.engine.book) for st in self._lanes]
