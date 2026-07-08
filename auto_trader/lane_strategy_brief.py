"""Daily AI strategy brief — markdown report for user review."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from auto_trader.lane_analyzer import analyze_lane_session, rank_lanes
from auto_trader.lane_version import LaneVersion, load_active_lanes_map, load_lane_version
from auto_trader.session_report import book_to_session_dict

if TYPE_CHECKING:
    from auto_trader.parallel_runner import ParallelDailyRunner

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "logs" / "reports"


def _ai_strategy_lines(session: dict[str, Any], next_lv: LaneVersion | None) -> list[str]:
    analysis = session.get("analysis") or analyze_lane_session(session)
    stats = session.get("stats") or {}
    cond = session.get("condition_name", "?")
    vid = session.get("version_id", "?")
    pnl = float(stats.get("realized_pnl", 0))
    entries = int(stats.get("entries", 0))
    exits = int(stats.get("exits", 0))
    grade = analysis.get("grade", "?")

    lines = [f"### {cond} (`{vid}`) — 등급 **{grade}**", ""]
    lines.append(f"- 오늘: 진입 {entries} · 청산 {exits} · 손익 **{pnl:+,.0f}원**")
    lines.append(f"- 요약: {analysis.get('summary', '')}")
    lines.append("")
    lines.append("**개선 포인트**")
    for imp in analysis.get("improvements") or []:
        lines.append(f"- {imp}")
    lines.append("")
    if next_lv:
        lines.append(f"**내일 테스트 버전: `{next_lv.version_id}`**")
        if next_lv.changelog:
            lines.append(f"- 변경: {next_lv.changelog}")
        daily = next_lv.daily or {}
        filters = next_lv.filters or {}
        lines.append("- 적용 파라미터:")
        for k in (
            "min_execution_strength",
            "min_sell_balance_pct",
            "take_profit_pct",
            "stop_loss_pct",
            "trail_from_peak_pct",
            "max_positions",
        ):
            v = daily.get(k, filters.get(k))
            if v is not None:
                lines.append(f"  - {k}: {v}")
        lines.append("")
        lines.append("**내일 AI 전략**")
        if entries == 0:
            lines.append(
                f"- `{cond}` 조건식은 종목은 포착했으나 필터가 막았을 수 있음. "
                f"내일 `{next_lv.version_id}`에서 진입 문턱을 낮춰 데이터를 더 수집."
            )
        elif pnl < 0:
            lines.append(
                f"- 손실 구간 → 내일은 손절·동시보유를 보수적으로, "
                f"체결강도 기준을 소폭 상향해 질 낮은 진입을 줄임."
            )
        elif pnl > 0:
            lines.append(
                f"- 수익 구간 → 내일은 익절·고점추적을 유지하며 표본을 늘려 재현성 확인."
            )
        else:
            lines.append("- 표본 부족 → 내일 동일 조건으로 추가 데이터 수집 후 재평가.")
    else:
        lines.append("**내일 버전:** 자동 생성 예정 (장마감 후)")
    lines.append("")
    return lines


def write_daily_strategy_brief(
    runner: "ParallelDailyRunner",
    lanes: list[LaneVersion],
    *,
    day: datetime | None = None,
) -> Path:
    now = day or datetime.now()
    ymd = now.strftime("%y%m%d")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{ymd}_전략브리프.md"
    latest = REPORTS_DIR / "LATEST.md"

    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_map: dict[str, LaneVersion] = {}
    for cond, vid in load_active_lanes_map(tomorrow).items():
        nlv = load_lane_version(vid, cond)
        if nlv:
            tomorrow_map[cond] = nlv

    sessions: list[dict] = []
    for lv, book in runner.all_lane_books():
        s = book_to_session_dict(book, rev_id=lv.version_id, condition_names=[lv.condition_name])
        s["version_id"] = lv.version_id
        s["condition_name"] = lv.condition_name
        s["analysis"] = analyze_lane_session(s)
        sessions.append(s)
    ranked = rank_lanes(sessions)

    lines = [
        f"# 캐치 병렬 테스트 일일 브리프 — {now.strftime('%Y-%m-%d')}",
        "",
        "> UI 없이 수집된 모의매매 데이터 + 내일 자동 개선 전략",
        "",
        "## 오늘 결과 순위",
        "",
    ]
    for i, s in enumerate(ranked, 1):
        stats = s.get("stats") or {}
        pnl = float(stats.get("realized_pnl", 0))
        lines.append(
            f"{i}. **{s.get('condition_name')}** `{s.get('version_id')}` "
            f"— {pnl:+,.0f}원 (승률 {stats.get('win_rate', 0)}%)"
        )
    lines.extend(["", "## 조건별 AI 전략 (내일)", ""])
    for s in ranked:
        cond = s.get("condition_name", "")
        next_lv = tomorrow_map.get(cond)
        lines.extend(_ai_strategy_lines(s, next_lv))

    lines.extend(
        [
            "## 데이터 파일",
            "",
            f"- 체결 CSV: `logs/lanes/<버전>/daily_{now:%Y%m%d}.csv`",
            f"- 세션 JSON: `logs/sessions/lanes/`",
            f"- 버전 정의: `strategies/lanes/<조건식>/`",
            "",
            "---",
            f"*생성: {now.strftime('%Y-%m-%d %H:%M:%S')} · 매일 장마감 후 자동 갱신*",
        ]
    )

    text = "\n".join(lines)
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    logger.info("strategy brief written: %s", path)
    return path
