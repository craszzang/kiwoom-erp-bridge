"""End-of-day lane analysis — what to improve per condition."""

from __future__ import annotations

from typing import Any


def _count_reason(session: dict[str, Any], prefix: str) -> int:
    return sum(1 for t in session.get("closed_trades") or [] if str(t.get("reason", "")).startswith(prefix))


def analyze_lane_session(session: dict[str, Any]) -> dict[str, Any]:
    stats = session.get("stats") or {}
    entries = int(stats.get("entries", 0))
    exits = int(stats.get("exits", 0))
    wins = int(stats.get("wins", 0))
    losses = int(stats.get("losses", 0))
    pnl = float(stats.get("realized_pnl", 0))
    win_rate = wins / exits if exits else 0.0

    improvements: list[str] = []
    grade = "B"

    if entries == 0:
        improvements.append("진입 0건 → 조건식 종목은 나왔으나 호가 필터(매도잔량·체결강도)가 과함. 필터 완화 검토")
        grade = "D"
    elif entries <= 2 and exits <= 1:
        improvements.append("진입이 적음 → min_execution_strength·min_sell_balance_pct 소폭 완화")
        grade = "C"

    if exits >= 3 and pnl < 0:
        improvements.append("실현손익 마이너스 → 손절폭 축소·동시보유 종목 수 감소")
        grade = "D" if pnl < -30000 else "C"

    stop_exits = _count_reason(session, "SELL_STOP")
    if stop_exits >= 2:
        improvements.append("손절 다발 → 진입 타이밍(체결강도 상향) 또는 손절폭 조정")

    trail_exits = _count_reason(session, "SELL_TRAIL")
    rsi_exits = _count_reason(session, "SELL_RSI")
    if trail_exits + rsi_exits >= 2 and pnl > 0:
        improvements.append("고점/RSI 청산으로 수익 확보 양호 → 익절·추적폭 유지 또는 소폭 확대")

    if exits >= 3 and win_rate >= 0.55 and pnl > 0:
        improvements.append("승률·수익 양호 → 현 조건식 유지, 익절 목표 소폭 상향 가능")
        grade = "A"

    if not improvements:
        improvements.append("표본 부족 → 동일 버전으로 내일 추가 테스트 권장")

    summary_parts = [
        f"진입{entries} 청산{exits} 승{wins}/패{losses}",
        f"손익{pnl:+,.0f}원",
        f"승률{win_rate * 100:.0f}%",
    ]
    return {
        "grade": grade,
        "summary": " | ".join(summary_parts),
        "improvements": improvements,
        "entries": entries,
        "exits": exits,
        "pnl": pnl,
        "win_rate": round(win_rate * 100, 1),
    }


def rank_lanes(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(s: dict[str, Any]) -> float:
        stats = s.get("stats") or {}
        pnl = float(stats.get("realized_pnl", 0))
        wr = float(stats.get("win_rate", 0))
        ex = int(stats.get("exits", 0))
        return pnl + wr * 100 + ex * 500

    return sorted(sessions, key=score, reverse=True)
