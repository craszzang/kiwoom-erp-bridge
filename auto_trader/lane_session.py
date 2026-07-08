"""Prepare / finalize parallel condition-lane sessions."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from auto_trader.condition_picker import ConditionChoice
from auto_trader.lane_analyzer import analyze_lane_session, rank_lanes
from auto_trader.lane_evolver import save_next_day_lanes
from auto_trader.lane_version import LaneVersion, ensure_lane_for_condition, set_active_lanes
from auto_trader.session_report import book_to_session_dict
from auto_trader.telegram_notify import load_telegram_config, send_session_report

if TYPE_CHECKING:
    from auto_trader.config import TraderConfig
    from auto_trader.parallel_runner import ParallelDailyRunner

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "logs" / "sessions" / "lanes"


def prepare_parallel_lanes(
    config: "TraderConfig",
    conditions: list[ConditionChoice],
) -> list[LaneVersion]:
    max_n = int(getattr(getattr(config, "strategy_auto", None), "max_parallel_conditions", 8) or 8)
    picked = conditions[:max_n]
    lanes: list[LaneVersion] = []
    active_map: dict[str, str] = {}
    for cond in picked:
        lv = ensure_lane_for_condition(cond.name, cond.index)
        lanes.append(lv)
        active_map[cond.name] = lv.version_id
        logger.info("lane ready %s %s", cond.name, lv.version_id)
    if active_map:
        set_active_lanes(active_map)
    return lanes


def _session_path(session: dict) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    day = session.get("date", datetime.now().strftime("%Y-%m-%d"))
    cond = session.get("condition_name", "lane")
    vid = str(session.get("version_id", "")).lstrip(".").replace(".", "_")
    safe_cond = cond.replace("/", "_")[:40]
    return SESSIONS_DIR / f"{day}_{safe_cond}_{vid}.json"


def save_lane_session_report(session: dict) -> Path:
    path = _session_path(session)
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("lane session saved: %s", path.name)
    return path


def finalize_parallel_session(
    config: "TraderConfig",
    runner: "ParallelDailyRunner | None",
    condition_names: list[str] | None = None,
) -> None:
    if not runner:
        logger.warning("finalize_parallel: no runner")
        return

    lane_versions: dict[str, LaneVersion] = {}
    sessions: list[dict] = []
    for lv, book in runner.all_lane_books():
        lane_versions[lv.condition_name] = lv
        analysis = analyze_lane_session(
            book_to_session_dict(book, rev_id=lv.version_id, condition_names=[lv.condition_name])
        )
        session = book_to_session_dict(
            book,
            rev_id=lv.version_id,
            condition_names=[lv.condition_name],
        )
        session["version_id"] = lv.version_id
        session["condition_name"] = lv.condition_name
        session["lane_title"] = lv.title
        session["analysis"] = analysis
        session["improvements"] = analysis.get("improvements") or []
        save_lane_session_report(session)
        sessions.append(session)

    ranked = rank_lanes(sessions)
    if ranked:
        best = ranked[0]
        logger.info(
            "lane rank #1 %s %s pnl=%s",
            best.get("condition_name"),
            best.get("version_id"),
            (best.get("stats") or {}).get("realized_pnl"),
        )

    auto_evolve = getattr(config, "strategy_auto", None)
    evolve_on = True if auto_evolve is None else bool(getattr(auto_evolve, "auto_evolve", True))
    next_lanes: list[LaneVersion] = []
    if evolve_on and sessions:
        next_lanes = save_next_day_lanes(sessions, lane_versions)
        tomorrow_map = {lv.condition_name: lv.version_id for lv in next_lanes}
        if tomorrow_map:
            from datetime import timedelta

            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            set_active_lanes(tomorrow_map, tomorrow)

    if runner and sessions:
        try:
            from auto_trader.lane_strategy_brief import write_daily_strategy_brief

            lanes_list = list(lane_versions.values())
            write_daily_strategy_brief(runner, lanes_list)
        except Exception as exc:
            logger.warning("strategy brief failed: %s", exc)

    tg_cfg = load_telegram_config()
    if tg_cfg.enabled and sessions:
        msg = _format_parallel_telegram(sessions, ranked, next_lanes)
        ok = send_session_report(msg)
        logger.info("telegram parallel report sent=%s", ok)


def _format_parallel_telegram(
    sessions: list[dict],
    ranked: list[dict],
    next_lanes: list[LaneVersion],
) -> str:
    day = sessions[0].get("date", "") if sessions else ""
    lines = [f"🤖 <b>병렬 조건식 일일 리포트</b>", f"📅 {day}", ""]
    for i, s in enumerate(ranked[:8], 1):
        stats = s.get("stats") or {}
        pnl = float(stats.get("realized_pnl", 0))
        emoji = "📈" if pnl >= 0 else "📉"
        analysis = s.get("analysis") or {}
        lines.append(
            f"{i}. <b>{s.get('condition_name')}</b> {s.get('version_id')} "
            f"{emoji} {pnl:+,.0f}원 | 승률{stats.get('win_rate', 0)}%"
        )
        for imp in (analysis.get("improvements") or [])[:2]:
            lines.append(f"   ↳ {imp}")
    if next_lanes:
        lines.extend(["", "<b>내일 테스트 버전</b>"])
        for lv in next_lanes[:8]:
            lines.append(f"• {lv.condition_name} → <b>{lv.version_id}</b>")
            if lv.changelog:
                lines.append(f"  {lv.changelog[:120]}")
    lines.append("")
    lines.append("<i>중지: 자율모의-중지.bat</i>")
    return "\n".join(lines)
