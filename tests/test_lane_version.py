"""Tests for lane version naming and analysis."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_trader.lane_analyzer import analyze_lane_session, rank_lanes
from auto_trader.lane_version import (
    LaneVersion,
    make_version_id,
    next_version_for_date,
    parse_version_id,
    save_lane_version,
    load_lane_version,
)


def test_version_id_format() -> None:
    vid = make_version_id(datetime(2026, 7, 8), 1)
    assert vid == ".260708_ver.1"
    parsed = parse_version_id(vid)
    assert parsed == ("260708", 1)


def test_next_version_increments() -> None:
    # Unique condition name per run → isolated from leftover lane files.
    cond = f"테스트조건_{int(datetime.now().timestamp())}"
    d = datetime(2026, 7, 8)
    v1 = next_version_for_date(cond, d)
    assert v1 == ".260708_ver.1"
    lv = LaneVersion(
        version_id=v1,
        condition_name=cond,
        condition_index=0,
        trade_date="2026-07-08",
        daily={"enabled": True},
    )
    save_lane_version(lv)
    v2 = next_version_for_date(cond, d)
    assert v2 == ".260708_ver.2"
    loaded = load_lane_version(v1, cond)
    assert loaded is not None
    assert loaded.version_id == v1


def test_analyze_no_entries() -> None:
    session = {
        "stats": {"entries": 0, "exits": 0, "wins": 0, "losses": 0, "realized_pnl": 0},
        "closed_trades": [],
    }
    out = analyze_lane_session(session)
    assert out["grade"] == "D"
    assert out["improvements"]


def test_rank_lanes() -> None:
    a = {"stats": {"realized_pnl": 10000, "win_rate": 60, "exits": 3}}
    b = {"stats": {"realized_pnl": -5000, "win_rate": 30, "exits": 2}}
    ranked = rank_lanes([b, a])
    assert ranked[0] is a


if __name__ == "__main__":
    test_version_id_format()
    test_next_version_increments()
    test_analyze_no_entries()
    test_rank_lanes()
    print("ALL OK")
