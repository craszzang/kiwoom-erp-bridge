"""Estimate 호가/체결강도 from OHLCV (backtest only)."""

from __future__ import annotations

from .bars import Bar5


def estimate_sell_balance_pct(bar: Bar5) -> float:
    """Close near high -> lower sell% (more buy side)."""
    rng = bar.high - bar.low
    if rng <= 0:
        return 50.0
    return 50.0 + (bar.high - bar.close) / rng * 50.0


def estimate_order_totals(bar: Bar5) -> tuple[int, int]:
    sell_pct = estimate_sell_balance_pct(bar)
    total = max(bar.volume, 1)
    sell_total = int(total * sell_pct / 100.0)
    buy_total = max(0, total - sell_total)
    if sell_total <= buy_total:
        sell_total = buy_total + max(1, int(total * 0.04))
    return sell_total, buy_total


def estimate_execution_strength(bar: Bar5, history: list[Bar5], lookback: int = 12) -> float:
    """
    Proxy for Kiwoom 체결강도 (100 = neutral).
    Up-volume vs down-volume over recent bars.
    """
    window = history[-lookback:] if history else [bar]
    buy_vol = 0.0
    sell_vol = 0.0
    for b in window:
        if b.close >= b.open:
            buy_vol += b.volume
        else:
            sell_vol += b.volume
    if sell_vol <= 0:
        return 130.0 if buy_vol > 0 else 100.0
    ratio = buy_vol / sell_vol
    return max(50.0, min(250.0, ratio * 100.0))
