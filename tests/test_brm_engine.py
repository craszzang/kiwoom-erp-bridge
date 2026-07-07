"""Unit tests for BRM engine (no Kiwoom required)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_trader.brm_engine import BrmAction, BrmEngine, MarketContext
from auto_trader.brm_params import BrmParams
from auto_trader.minute_bars import MinuteBar, MinuteBarStore


def _make_spring_bars(n: int = 30, spring_at: int = -1) -> MinuteBarStore:
    store = MinuteBarStore(code="005930")
    base = datetime(2026, 6, 15, 9, 0)
    price = 10000.0
    for i in range(n):
        dt = base + timedelta(minutes=i)
        lo = price - 50
        hi = price + 30
        cl = price - 10
        if i == spring_at:
            lo = price - 200
            cl = price + 20
        store.bars.append(
            MinuteBar(dt=dt, open=price, high=hi, low=lo, close=cl, volume=1000 + i * 10)
        )
        price = cl
    return store


def test_session_force_flat_at_11() -> None:
    params = BrmParams(session_end="11:00", stop_loss_pct=99)
    engine = BrmEngine(params)
    engine.book.open_or_add("005930", "Samsung", 1, 10000, datetime(2026, 6, 15, 9, 30), is_add=False)
    store = _make_spring_bars(20)
    ctx = MarketContext(
        price=10050,
        sell_balance_pct=60,
        execution_strength=120,
        now=datetime(2026, 6, 15, 11, 0),
    )
    sig = engine.evaluate("005930", "Samsung", store, ctx)
    assert sig.action == BrmAction.TIME_FLAT


def test_stop_loss_triggers() -> None:
    params = BrmParams(stop_loss_pct=3.0)
    engine = BrmEngine(params)
    engine.book.open_or_add("005930", "Samsung", 1, 10000, datetime(2026, 6, 15, 9, 30), is_add=False)
    store = _make_spring_bars(25)
    ctx = MarketContext(
        price=9600,
        sell_balance_pct=55,
        execution_strength=90,
        now=datetime(2026, 6, 15, 10, 0),
    )
    sig = engine.evaluate("005930", "Samsung", store, ctx)
    assert sig.action == BrmAction.STOP


def test_no_entry_outside_session() -> None:
    params = BrmParams()
    engine = BrmEngine(params)
    store = _make_spring_bars(30, spring_at=28)
    ctx = MarketContext(
        price=10000,
        sell_balance_pct=60,
        execution_strength=120,
        now=datetime(2026, 6, 15, 8, 50),
    )
    sig = engine.evaluate("005930", "Samsung", store, ctx)
    assert sig.action == BrmAction.NONE


def test_take_profit() -> None:
    params = BrmParams(tp_pct=1.5)
    engine = BrmEngine(params)
    engine.book.open_or_add("005930", "Samsung", 1, 10000, datetime(2026, 6, 15, 9, 30), is_add=False)
    store = _make_spring_bars(20)
    ctx = MarketContext(
        price=10160,
        sell_balance_pct=55,
        execution_strength=110,
        now=datetime(2026, 6, 15, 10, 15),
    )
    sig = engine.evaluate("005930", "Samsung", store, ctx)
    assert sig.action == BrmAction.TP
