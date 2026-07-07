"""Tests for strategy evolution (no Kiwoom)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_trader.strategy_optimizer import evolve_strategy
from auto_trader.strategy_rev import StrategyRev, ensure_baseline_rev, next_rev_id, save_rev


def test_baseline_rev_exists() -> None:
    rev = ensure_baseline_rev()
    assert rev.rev_id == "Rev.0"
    assert rev.brm.get("tp_pct") == 1.2


def test_evolve_on_loss_session() -> None:
    rev = ensure_baseline_rev()
    session = {
        "stats": {
            "entries": 5,
            "exits": 4,
            "wins": 1,
            "losses": 3,
            "realized_pnl": -50000,
        },
        "closed_trades": [
            {"reason": "STOP"},
            {"reason": "STOP"},
            {"reason": "TP"},
        ],
        "late_entries": 0,
    }
    new_rev = evolve_strategy(rev, session)
    assert new_rev is not None
    assert new_rev.rev_id != rev.rev_id
    assert float(new_rev.brm["stop_loss_pct"]) < float(rev.brm["stop_loss_pct"])


def test_no_evolve_on_empty_session() -> None:
    rev = ensure_baseline_rev()
    session = {"stats": {"entries": 0, "exits": 0, "wins": 0, "losses": 0, "realized_pnl": 0}}
    assert evolve_strategy(rev, session) is None


def test_next_rev_id_increments() -> None:
    save_rev(StrategyRev(rev_id="Rev.99", title="t", description="", created_at=""))
    assert next_rev_id() == "Rev.100"
