"""Evolve lane versions for next trading day."""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timedelta
from typing import Any

from auto_trader.lane_analyzer import analyze_lane_session
from auto_trader.lane_version import LaneVersion, make_version_id, save_lane_version
from auto_trader.strategy_optimizer import evolve_strategy
from auto_trader.strategy_rev import StrategyRev

logger = logging.getLogger(__name__)


def _lane_to_rev(lv: LaneVersion) -> StrategyRev:
    return StrategyRev(
        rev_id=lv.version_id,
        title=lv.title or lv.condition_name,
        description="",
        created_at=lv.created_at,
        daily=dict(lv.daily),
        filters=dict(lv.filters),
        condition_keywords=[lv.condition_name],
        parent_rev=lv.parent_version,
    )


def evolve_lane_version(
    lv: LaneVersion,
    session: dict[str, Any],
    *,
    next_day: datetime | None = None,
) -> LaneVersion:
    analysis = analyze_lane_session(session)
    rev = _lane_to_rev(lv)
    evolved = evolve_strategy(rev, session)

    daily = copy.deepcopy(lv.daily)
    filters = copy.deepcopy(lv.filters)
    changelog = lv.changelog

    if evolved:
        daily.update(evolved.daily or {})
        if evolved.filters:
            filters.update(evolved.filters)
        changelog = evolved.changelog or changelog
    elif analysis.get("improvements"):
        changelog = " | ".join(analysis["improvements"][:2])

    nd = next_day or (datetime.now() + timedelta(days=1))
    new_vid = make_version_id(nd, 1)
    return LaneVersion(
        version_id=new_vid,
        condition_name=lv.condition_name,
        condition_index=lv.condition_index,
        trade_date=nd.strftime("%Y-%m-%d"),
        title=lv.title,
        daily=daily,
        filters=filters,
        parent_version=lv.version_id,
        changelog=changelog,
        analysis_summary=analysis.get("summary", ""),
        improvements=list(analysis.get("improvements") or []),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )


def save_next_day_lanes(
    lane_sessions: list[dict[str, Any]],
    lane_versions: dict[str, LaneVersion],
) -> list[LaneVersion]:
    """Create tomorrow's ver.1 files from today's lane results."""
    next_day = datetime.now() + timedelta(days=1)
    out: list[LaneVersion] = []
    for session in lane_sessions:
        cond = session.get("condition_name") or ""
        if not cond:
            continue
        parent = lane_versions.get(cond)
        if not parent:
            continue
        nlv = evolve_lane_version(parent, session, next_day=next_day)
        save_lane_version(nlv)
        out.append(nlv)
        logger.info("next lane %s %s — %s", cond, nlv.version_id, nlv.changelog[:80])
    return out
