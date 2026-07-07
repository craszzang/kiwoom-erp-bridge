"""당일매매 자동 실행 (조건식 + 실시간 호가)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from PyQt5.QtCore import QTimer

from auto_trader.daily_engine import DailyEngine
from auto_trader.daily_params import DailyParams
from auto_trader.minute_bars import MinuteBarLoader

if TYPE_CHECKING:
    from auto_trader.config import TraderConfig
    from auto_trader.kiwoom_api import KiwoomAPI
    from auto_trader.stock_scanner import ConditionStockScanner

logger = logging.getLogger(__name__)


class DailyRunner:
    def __init__(
        self,
        api: "KiwoomAPI",
        config: "TraderConfig",
        scanner: "ConditionStockScanner",
        params: DailyParams | None = None,
        on_update: Callable[[], None] | None = None,
    ) -> None:
        self.api = api
        self.config = config
        self.scanner = scanner
        self.params = params or getattr(config, "daily", DailyParams())
        self.engine = DailyEngine(self.params)
        self._on_update = on_update
        self._loader = MinuteBarLoader(api, getattr(config, "brm_tr_screen_no", "0104"), bar_minutes=1)
        self._active = False
        self._tick = QTimer()
        self._tick.setInterval(max(300, self.params.tick_ms))
        self._tick.timeout.connect(self._on_tick)
        self._prev = scanner.on_state_change

        def chained() -> None:
            if self._prev:
                self._prev()

        scanner.on_state_change = chained

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        codes = self._codes()
        self._loader.enqueue(codes[: self.params.max_symbols])
        self._tick.start()
        logger.info("DailyRunner start symbols=%d paper=%s", len(codes), self.params.paper_only)

    def stop(self) -> None:
        self._active = False
        self._tick.stop()

    def _codes(self) -> list[str]:
        passed = self.scanner.filtered_quotes()
        if passed:
            return [q.code for q in passed]
        return [q.code for q in self.scanner.display_quotes()[: self.params.max_symbols]]

    def _on_tick(self) -> None:
        if not self._active:
            return
        now = datetime.now()
        for code in self._codes()[: self.params.max_symbols]:
            q = self.scanner.quotes.get(code)
            if not q or q.price <= 0:
                continue
            store = self._loader.store(code)
            if q.cum_volume:
                store.update_cum_volume(int(q.cum_volume), now)
            store.update_tick(float(q.price), now)
            sig = self.engine.evaluate(
                code, q.name or code, float(q.price),
                q.sell_balance_pct, q.execution_strength,
                q.sell_total, q.buy_total, now, store,
            )
            if sig.action.value != "NONE":
                if not self.params.paper_only:
                    self._send_order(sig)
                self.engine.apply_signal(sig, now)
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
        s = self.engine.book.stats
        return (
            f"당일매매 | 진입{s.entries} 청산{s.exits} "
            f"승{s.wins}/패{s.losses} 보유{len(self.engine.book.positions)} "
            f"손익{s.realized_pnl:+,.0f}"
        )
