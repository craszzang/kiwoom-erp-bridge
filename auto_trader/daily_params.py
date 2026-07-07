"""Daily scalping parameters (당일매수·당일매도)."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import time
from typing import Any


def _parse_hm(text: str, default: tuple[int, int]) -> time:
    raw = str(text).strip()
    if ":" in raw:
        h, m = raw.split(":", 1)
        return time(int(h), int(m))
    return time(default[0], default[1])


@dataclass
class DailyParams:
    enabled: bool = True
    paper_only: bool = True

    session_start: str = "09:05"
    session_end: str = "15:20"
    entry_cutoff: str = "14:30"
    force_flat: str = "15:20"

    min_sell_balance_pct: float = 52.0
    min_execution_strength: float = 110.0
    exit_strength_below: float = 95.0
    exit_sell_balance_below: float = 48.0

    take_profit_pct: float = 2.0
    stop_loss_pct: float = 2.5
    trail_from_peak_pct: float = 0.6
    min_profit_to_trail_pct: float = 0.35

    max_positions: int = 3
    base_qty: int = 1
    max_symbols: int = 40
    tick_ms: int = 600
    log_signals: bool = True

    rsi_period: int = 14
    rsi_exit_high: float = 72.0
    use_rsi_peak_exit: bool = True

    @property
    def t_session_start(self) -> time:
        return _parse_hm(self.session_start, (9, 5))

    @property
    def t_session_end(self) -> time:
        return _parse_hm(self.session_end, (15, 20))

    @property
    def t_entry_cutoff(self) -> time:
        return _parse_hm(self.entry_cutoff, (14, 30))

    @property
    def t_force_flat(self) -> time:
        return _parse_hm(self.force_flat, (15, 20))

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "DailyParams":
        if not raw:
            return cls()
        kwargs: dict[str, Any] = {}
        valid = {f.name for f in fields(cls)}
        for k, v in raw.items():
            if k in valid:
                kwargs[k] = v
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}
