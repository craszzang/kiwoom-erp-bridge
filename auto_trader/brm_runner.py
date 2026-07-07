"""BRM paper-test runner: Kiwoom real-time + minute bars + engine."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from PyQt5.QtCore import QTimer

from auto_trader.brm_engine import BrmEngine, MarketContext
from auto_trader.brm_params import BrmParams
from auto_trader.minute_bars import MinuteBarLoader

if TYPE_CHECKING:
    from auto_trader.config import TraderConfig
    from auto_trader.kiwoom_api import KiwoomAPI
    from auto_trader.stock_scanner import ConditionStockScanner, StockQuote

logger = logging.getLogger(__name__)

FID_CUM_VOLUME = 13


class BrmPaperRunner:
    """Runs BRM v3 paper tests on scanner watchlist during 09:00-11:00."""

    def __init__(
        self,
        api: "KiwoomAPI",
        config: "TraderConfig",
        scanner: "ConditionStockScanner",
        params: BrmParams | None = None,
        on_update: Callable[[], None] | None = None,
    ) -> None:
        self.api = api
        self.config = config
        self.scanner = scanner
        self.params = params or getattr(config, "brm", BrmParams())
        self.engine = BrmEngine(self.params)
        self._on_update = on_update
        self._loader = MinuteBarLoader(
            api=api,
            screen_no=getattr(config, "brm_tr_screen_no", "0104"),
            bar_minutes=self.params.bar_minutes,
        )
        self._last_cum_vol: dict[str, int] = {}
        self._active = False
        self._tick_timer = QTimer()
        self._tick_timer.setInterval(800)
        self._tick_timer.timeout.connect(self._on_tick)
        self._prev_real = scanner.on_state_change

        def chained() -> None:
            if self._prev_real:
                self._prev_real()
            if self._active:
                self._sync_quotes()

        scanner.on_state_change = chained

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self.params.enabled = True
        self._active = True
        codes = self._target_codes()
        logger.info("BRM paper start: %d symbols", len(codes))
        self._loader.enqueue(codes[: self.params.max_symbols], on_done=self._on_bars_ready)
        self._tick_timer.start()

    def stop(self) -> None:
        self._active = False
        self._tick_timer.stop()
        self.params.enabled = False

    def _target_codes(self) -> list[str]:
        passed = self.scanner.filtered_quotes()
        if passed:
            return [q.code for q in passed]
        rows = self.scanner.display_quotes()
        return [q.code for q in rows[: self.params.max_symbols]]

    def _on_bars_ready(self) -> None:
        logger.info("BRM minute bars preload done (%d stores)", len(self._loader.stores()))
        if self._on_update:
            self._on_update()

    def _sync_quotes(self) -> None:
        now = datetime.now()
        for code, quote in list(self.scanner.quotes.items()):
            if quote.price <= 0:
                continue
            store = self._loader.store(code)
            cum = int(quote.cum_volume or 0)
            if cum > 0:
                prev = self._last_cum_vol.get(code)
                tick_vol = max(0, cum - prev) if prev is not None else 0
                self._last_cum_vol[code] = cum
                store.update_cum_volume(cum, now)
                store.update_tick(float(quote.price), now, tick_vol)
            else:
                store.update_tick(float(quote.price), now, 0)

    def _on_tick(self) -> None:
        if not self._active:
            return
        now = datetime.now()
        self._sync_quotes()
        for code in self._target_codes()[: self.params.max_symbols]:
            quote = self.scanner.quotes.get(code)
            if not quote or quote.price <= 0:
                continue
            store = self._loader.store(code)
            if len(store.bars) < 5:
                continue
            ctx = MarketContext(
                price=float(quote.price),
                sell_balance_pct=quote.sell_balance_pct,
                execution_strength=quote.execution_strength,
                now=now,
            )
            sig = self.engine.evaluate(code, quote.name or code, store, ctx)
            if sig.action.value != "NONE":
                self.engine.apply_signal(sig, now)
        if self._on_update:
            self._on_update()

    def status_text(self) -> str:
        s = self.engine.book.stats
        open_n = len(self.engine.book.positions)
        return (
            f"BRM 모의 | 진입{s.entries} 추매{s.adds} 청산{s.exits} "
            f"승{s.wins}/패{s.losses} 보유{open_n} "
            f"손익{s.realized_pnl:+,.0f}"
        )
