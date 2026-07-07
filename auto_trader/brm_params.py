"""BRM v3 scalping parameters (configurable)."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import time
from typing import Any


def _parse_hm(text: str, default: tuple[int, int]) -> time:
    raw = str(text).strip()
    if ":" in raw:
        h, m = raw.split(":", 1)
        return time(int(h), int(m))
    if len(raw) == 4 and raw.isdigit():
        return time(int(raw[:2]), int(raw[2:]))
    return time(default[0], default[1])


@dataclass
class BrmParams:
    """Top Trader BRM v3 + 단타(09~11) + 손절."""

    enabled: bool = False
    paper_only: bool = True

    session_start: str = "09:00"
    session_end: str = "11:00"
    entry_cutoff: str = "10:30"

    low_depth: int = 3
    low_offset: int = 6
    rsi_entry_max: float = 65.0
    rsi_add_max: float = 50.0

    martin_trigger_pct: float = 0.2
    add_limit_pct: float = 3.0
    martin_ratio: float = 1.0
    max_entries: int = 4
    base_qty: int = 1

    tp_pct: float = 1.5
    tp_min_profit_pct: float = 0.5
    rsi_exit_min: float = 70.0
    stop_loss_pct: float = 5.0

    rsi_period: int = 14
    bb_length: int = 200
    bb_mult: float = 1.5
    macd_fast: int = 6
    macd_slow: int = 12
    macd_signal: int = 5

    min_sell_balance_pct: float = 50.0
    min_execution_strength: float = 100.0
    add_min_sell_balance_pct: float = 45.0
    add_min_execution_strength: float = 80.0

    min_session_volume: int = 0
    volume_surge_ratio: float = 1.5
    require_volume_surge: bool = False

    bar_minutes: int = 1
    max_symbols: int = 40
    log_signals: bool = True

    @property
    def t_session_start(self) -> time:
        return _parse_hm(self.session_start, (9, 0))

    @property
    def t_session_end(self) -> time:
        return _parse_hm(self.session_end, (11, 0))

    @property
    def t_entry_cutoff(self) -> time:
        return _parse_hm(self.entry_cutoff, (10, 30))

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "BrmParams":
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
