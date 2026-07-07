"""Post-session strategy evolution for daily + BRM revisions."""

from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Any

from auto_trader.strategy_rev import StrategyRev, next_rev_id, save_rev, set_active_rev

logger = logging.getLogger(__name__)


def _clone_daily(rev: StrategyRev) -> dict[str, Any]:
    return copy.deepcopy(rev.daily or rev.brm or {})


def _clone_filters(rev: StrategyRev) -> dict[str, Any]:
    return copy.deepcopy(rev.filters or {})


def evolve_strategy(rev: StrategyRev, session: dict[str, Any]) -> StrategyRev | None:
    stats = session.get("stats") or {}
    entries = int(stats.get("entries", 0))
    exits = int(stats.get("exits", 0))
    wins = int(stats.get("wins", 0))
    pnl = float(stats.get("realized_pnl", 0.0))
    win_rate = wins / exits if exits > 0 else 0.0

    daily = _clone_daily(rev)
    filters = _clone_filters(rev)
    changes: list[str] = []

    trail_exits = _count_exit_reasons(session, "SELL_TRAIL")
    stop_exits = _count_exit_reasons(session, "SELL_STOP")

    if exits >= 3 and pnl < 0:
        daily["stop_loss_pct"] = max(1.5, float(daily.get("stop_loss_pct", 2.5)) - 0.3)
        daily["take_profit_pct"] = max(1.2, float(daily.get("take_profit_pct", 2.0)) - 0.2)
        daily["max_positions"] = max(1, int(daily.get("max_positions", 3)) - 1)
        changes.append("손실 → 손절·익절·동시보유 축소")

    if exits >= 3 and win_rate >= 0.55 and pnl > 0:
        daily["take_profit_pct"] = min(3.5, float(daily.get("take_profit_pct", 2.0)) + 0.2)
        daily["trail_from_peak_pct"] = min(1.0, float(daily.get("trail_from_peak_pct", 0.6)) + 0.05)
        changes.append("수익 양호 → 익절·고점추적 여유 확대")

    if entries <= 1 and exits == 0:
        daily["min_execution_strength"] = max(90.0, float(daily.get("min_execution_strength", 110)) - 8)
        daily["min_sell_balance_pct"] = max(50.0, float(daily.get("min_sell_balance_pct", 52)) - 2)
        filters["min_execution_strength"] = daily["min_execution_strength"]
        filters["min_sell_balance_pct"] = daily["min_sell_balance_pct"]
        changes.append("진입 부족 → 호가 필터 완화")

    if stop_exits >= 2 and exits >= 3:
        daily["min_profit_to_trail_pct"] = max(0.25, float(daily.get("min_profit_to_trail_pct", 0.35)) - 0.05)
        changes.append("손절 다발 → 고점추적 최소이익 하향")

    if trail_exits >= 2 and pnl > 0:
        daily["trail_from_peak_pct"] = max(0.4, float(daily.get("trail_from_peak_pct", 0.6)) - 0.05)
        changes.append("고점매도 성공 → 추적폭 타이트")

    if not changes:
        return None

    new_id = next_rev_id()
    return StrategyRev(
        rev_id=new_id,
        title=f"{rev.title} 개선",
        description=rev.description,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        daily=daily,
        brm={"enabled": False},
        filters=filters or rev.filters,
        condition_keywords=list(rev.condition_keywords),
        changelog=" | ".join(changes),
        parent_rev=rev.rev_id,
    )


def _count_exit_reasons(session: dict[str, Any], action: str) -> int:
    trades = session.get("closed_trades") or []
    return sum(1 for t in trades if str(t.get("reason", "")).startswith(action))


def maybe_evolve_and_activate(rev: StrategyRev, session: dict[str, Any], *, auto_activate: bool = True) -> StrategyRev:
    new_rev = evolve_strategy(rev, session)
    if new_rev is None:
        return rev
    save_rev(new_rev)
    if auto_activate:
        set_active_rev(new_rev.rev_id)
    return new_rev
