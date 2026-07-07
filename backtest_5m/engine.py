"""Run daily strategy on 5-minute bar history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from auto_trader.daily_engine import DailyAction, DailyEngine
from auto_trader.daily_params import DailyParams
from auto_trader.minute_bars import MinuteBar, MinuteBarStore

from .bars import Bar5
from .proxies import estimate_execution_strength, estimate_order_totals, estimate_sell_balance_pct

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    code: str
    name: str
    bar_count: int
    stats: dict
    trades: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)


def _bars_to_store(code: str, bars: list[Bar5]) -> MinuteBarStore:
    store = MinuteBarStore(code=code)
    for b in bars:
        store.bars.append(
            MinuteBar(dt=b.dt, open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume)
        )
    return store


def run_backtest_on_bars(
    code: str,
    name: str,
    bars: list[Bar5],
    params: DailyParams,
) -> BacktestResult:
    if len(bars) < 20:
        logger.warning("%s: too few bars (%d)", code, len(bars))
        return BacktestResult(code, name, len(bars), {"entries": 0, "exits": 0, "wins": 0, "losses": 0, "realized_pnl": 0})

    engine = DailyEngine(params)
    history: list[Bar5] = []
    signals: list[dict] = []

    for i, bar in enumerate(bars):
        history.append(bar)
        store = _bars_to_store(code, history)
        sell_pct = estimate_sell_balance_pct(bar)
        strength = estimate_execution_strength(bar, history)
        sell_t, buy_t = estimate_order_totals(bar)

        sig = engine.evaluate(
            code,
            name,
            bar.close,
            sell_pct,
            strength,
            sell_t,
            buy_t,
            bar.dt,
            store,
        )
        if sig.action != DailyAction.NONE:
            engine.apply_signal(sig, bar.dt)
            signals.append(
                {
                    "time": bar.dt.strftime("%Y-%m-%d %H:%M"),
                    "action": sig.action.value,
                    "price": sig.price,
                    "qty": sig.qty,
                    "reason": sig.reason,
                    "sell_pct": round(sell_pct, 1),
                    "strength": round(strength, 1),
                }
            )

    book = engine.book
    stats = {
        "entries": book.stats.entries,
        "exits": book.stats.exits,
        "wins": book.stats.wins,
        "losses": book.stats.losses,
        "realized_pnl": round(book.stats.realized_pnl, 0),
        "win_rate": round(book.stats.wins / book.stats.exits * 100, 1) if book.stats.exits else 0.0,
    }
    return BacktestResult(
        code=code,
        name=name,
        bar_count=len(bars),
        stats=stats,
        trades=list(book.closed_trades),
        signals=signals,
    )
