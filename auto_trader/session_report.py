"""End-of-session report builder and persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from auto_trader.brm_engine import BrmPaperBook, BrmSessionStats

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "logs" / "sessions"


def _count_late_entries(day: str, cutoff_hm: str = "10:00") -> int:
    """Count ENTRY signals after cutoff from today's BRM CSV."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    path = log_dir / f"brm_paper_{day.replace('-', '')}.csv"
    if not path.is_file():
        path = log_dir / f"brm_paper_{day}.csv"
    if not path.is_file():
        return 0
    try:
        h, m = cutoff_hm.split(":")
        cutoff = int(h) * 60 + int(m)
    except ValueError:
        cutoff = 10 * 60
    count = 0
    try:
        import csv

        with path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("action") != "ENTRY":
                    continue
                t = row.get("time", "")
                if ":" not in t:
                    continue
                parts = t.split(":")
                if len(parts) < 2:
                    continue
                mins = int(parts[0]) * 60 + int(parts[1])
                if mins >= cutoff:
                    count += 1
    except (OSError, ValueError):
        return 0
    return count


def book_to_session_dict(
    book: BrmPaperBook,
    *,
    rev_id: str,
    condition_names: list[str],
    date: datetime | None = None,
) -> dict[str, Any]:
    now = date or datetime.now()
    stats = book.stats
    day = now.strftime("%Y-%m-%d")
    late_entries = _count_late_entries(day)
    return {
        "date": day,
        "time_end": now.strftime("%H:%M:%S"),
        "rev_id": rev_id,
        "conditions": condition_names,
        "stats": {
            "entries": stats.entries,
            "adds": stats.adds,
            "exits": stats.exits,
            "wins": stats.wins,
            "losses": stats.losses,
            "realized_pnl": round(stats.realized_pnl, 0),
            "win_rate": round(stats.wins / stats.exits * 100, 1) if stats.exits else 0.0,
            "open_positions": len(book.positions),
        },
        "closed_trades": book.closed_trades,
        "late_entries": late_entries,
    }


def save_session_report(session: dict[str, Any]) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    day = session.get("date", datetime.now().strftime("%Y-%m-%d"))
    path = SESSIONS_DIR / f"{day}.json"
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("session report saved: %s", path)
    return path


def format_telegram_message(session: dict[str, Any], rev_title: str = "") -> str:
    stats = session.get("stats") or {}
    rev_id = session.get("rev_id", "?")
    day = session.get("date", "")
    conditions = session.get("conditions") or []
    pnl = float(stats.get("realized_pnl", 0))
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    lines = [
        f"🤖 <b>캐치 모의매매 일일 리포트</b>",
        f"📅 {day}  |  전략 <b>{rev_id}</b>",
    ]
    if rev_title:
        lines.append(f"📋 {rev_title}")
    if conditions:
        lines.append(f"🔍 조건: {', '.join(conditions[:3])}")
    lines.extend(
        [
            "",
            f"{pnl_emoji} <b>실현손익: {pnl:+,.0f}원</b>",
            f"진입 {stats.get('entries', 0)} · 추매 {stats.get('adds', 0)} · 청산 {stats.get('exits', 0)}",
            f"승 {stats.get('wins', 0)} / 패 {stats.get('losses', 0)} "
            f"(승률 {stats.get('win_rate', 0):.1f}%)",
        ]
    )
    trades = session.get("closed_trades") or []
    if trades:
        lines.append("")
        lines.append("<b>청산 내역</b>")
        for t in trades[:8]:
            name = t.get("name", t.get("code", ""))
            pct = float(t.get("pnl_pct", 0))
            reason = t.get("reason", "")
            lines.append(f"• {name} {pct:+.2f}% ({reason})")
        if len(trades) > 8:
            lines.append(f"… 외 {len(trades) - 8}건")
    changelog = session.get("next_rev_changelog")
    if changelog:
        lines.extend(["", f"🔄 다음 전략 개선: {changelog}"])
    lines.append("")
    lines.append("<i>중지: 자율모의-중지.bat</i>")
    return "\n".join(lines)


def load_recent_sessions(limit: int = 10) -> list[dict[str, Any]]:
    if not SESSIONS_DIR.is_dir():
        return []
    paths = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)[:limit]
    out: list[dict[str, Any]] = []
    for p in paths:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return out
