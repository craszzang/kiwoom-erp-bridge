"""Remote stock scanner mirror fed by bridge WebSocket."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from auto_trader.config import TraderConfig
from auto_trader.stock_scanner import StockQuote


@dataclass
class RemoteStockScanner:
    config: TraderConfig
    quotes: dict[str, StockQuote] = field(default_factory=dict)
    condition_codes: list[str] = field(default_factory=list)
    last_condition_count: int = 0
    market_mode: bool = False
    lite_rows: bool = False
    on_state_change: Callable[[], None] | None = None

    def _notify(self) -> None:
        if self.on_state_change:
            self.on_state_change()

    def apply_meta(self, payload: dict) -> None:
        self.last_condition_count = int(payload.get("last_condition_count", 0))
        self.market_mode = bool(payload.get("market_mode", False))
        self.lite_rows = bool(payload.get("lite_rows", False))
        codes = payload.get("condition_codes") or []
        if codes:
            self.condition_codes = list(codes)

    def apply_snapshot(self, rows: list[dict]) -> None:
        for raw in rows:
            self._upsert_quote(raw)
        self._notify()

    def apply_delta(self, rows: list[dict]) -> None:
        for raw in rows:
            self._upsert_quote(raw)
        self._notify()

    def _upsert_quote(self, raw: dict) -> None:
        code = str(raw.get("code", "")).strip()
        if not code:
            return
        q = self.quotes.get(code)
        if q is None:
            q = StockQuote(code=code)
            self.quotes[code] = q
        q.name = str(raw.get("name") or q.name or "")
        q.price = int(raw.get("price") or q.price or 0)
        q.change_amount = int(raw.get("change_amount") or q.change_amount or 0)
        q.change_pct = float(raw.get("change_pct") or q.change_pct or 0.0)
        q.sell_total = int(raw.get("sell_total") or q.sell_total or 0)
        q.buy_total = int(raw.get("buy_total") or q.buy_total or 0)
        q.execution_strength = float(raw.get("execution_strength") or q.execution_strength or 0.0)

    def bootstrap(self, conditions: list | None = None) -> None:
        """Handled on host via RemoteBridgeClient.bootstrap()."""

    def refresh_condition_snapshot(self) -> int:
        """Handled on host via RemoteBridgeClient.refresh_snapshot()."""
        return 0

    def filtered_quotes(self) -> list[StockQuote]:
        min_sell = self.config.min_sell_balance_pct
        min_strength = self.config.min_execution_strength
        rows = [q for q in self.quotes.values() if q.passes_filter(min_sell, min_strength)]
        rows.sort(key=lambda q: (-q.sell_balance_pct, -q.execution_strength, q.name))
        return rows

    def display_quotes(self) -> list[StockQuote]:
        min_sell = self.config.min_sell_balance_pct
        min_strength = self.config.min_execution_strength
        if self.config.filter_pass_only:
            return self.filtered_quotes()

        rows = list(self.quotes.values())
        rows.sort(
            key=lambda q: (
                0 if q.filter_state(min_sell, min_strength) == "pass" else 1,
                0 if q.filter_state(min_sell, min_strength) == "wait" else 1,
                -q.sell_balance_pct,
                q.name,
            )
        )
        return rows
