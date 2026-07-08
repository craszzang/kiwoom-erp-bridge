"""Date-based lane versions: .260708_ver.1 per condition."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from auto_trader.daily_params import DailyParams

logger = logging.getLogger(__name__)

LANES_DIR = Path(__file__).resolve().parent.parent / "strategies" / "lanes"
ACTIVE_LANES_FILE = LANES_DIR / "active_lanes.json"
_VERSION_RE = re.compile(r"^\.(\d{6})_ver\.(\d+)$")


@dataclass
class LaneVersion:
    version_id: str
    condition_name: str
    condition_index: int
    trade_date: str
    title: str = ""
    daily: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, Any] = field(default_factory=dict)
    parent_version: str = ""
    changelog: str = ""
    analysis_summary: str = ""
    improvements: list[str] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LaneVersion":
        return cls(
            version_id=str(raw.get("version_id", "")),
            condition_name=str(raw.get("condition_name", "")),
            condition_index=int(raw.get("condition_index", 0)),
            trade_date=str(raw.get("trade_date", "")),
            title=str(raw.get("title", "")),
            daily=dict(raw.get("daily") or {}),
            filters=dict(raw.get("filters") or {}),
            parent_version=str(raw.get("parent_version", "")),
            changelog=str(raw.get("changelog", "")),
            analysis_summary=str(raw.get("analysis_summary", "")),
            improvements=list(raw.get("improvements") or []),
            created_at=str(raw.get("created_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def daily_params(self) -> DailyParams:
        base = DailyParams().to_dict()
        base.update(self.daily or {})
        if "min_sell_balance_pct" in self.filters:
            base["min_sell_balance_pct"] = self.filters["min_sell_balance_pct"]
        if "min_execution_strength" in self.filters:
            base["min_execution_strength"] = self.filters["min_execution_strength"]
        base["enabled"] = True
        base["paper_only"] = True
        base["log_signals"] = True
        return DailyParams.from_dict(base)


def make_version_id(day: datetime | None = None, ver: int = 1) -> str:
    d = day or datetime.now()
    return f".{d:%y%m%d}_ver.{ver}"


def parse_version_id(version_id: str) -> tuple[str, int] | None:
    m = _VERSION_RE.match(version_id.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2))


def condition_slug(name: str) -> str:
    slug = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
    return slug or "condition"


def lane_file(version_id: str, condition_name: str) -> Path:
    safe_ver = version_id.lstrip(".").replace(".", "_")
    return LANES_DIR / condition_slug(condition_name) / f"{safe_ver}.json"


def save_lane_version(lv: LaneVersion) -> Path:
    path = lane_file(lv.version_id, lv.condition_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lv.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_lane_version(version_id: str, condition_name: str) -> LaneVersion | None:
    path = lane_file(version_id, condition_name)
    if not path.is_file():
        return None
    try:
        return LaneVersion.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("load lane %s failed: %s", path.name, exc)
        return None


def list_lane_versions(condition_name: str | None = None) -> list[LaneVersion]:
    LANES_DIR.mkdir(parents=True, exist_ok=True)
    out: list[LaneVersion] = []
    pattern = f"{condition_slug(condition_name)}/*.json" if condition_name else "**/*.json"
    for path in sorted(LANES_DIR.glob(pattern)):
        if path.name == "active_lanes.json":
            continue
        try:
            out.append(LaneVersion.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def next_version_for_date(condition_name: str, day: datetime | None = None) -> str:
    d = day or datetime.now()
    ymd = d.strftime("%y%m%d")
    max_ver = 0
    for lv in list_lane_versions(condition_name):
        parsed = parse_version_id(lv.version_id)
        if parsed and parsed[0] == ymd:
            max_ver = max(max_ver, parsed[1])
    return make_version_id(d, max_ver + 1)


def baseline_lane_version(condition_name: str, condition_index: int, day: datetime | None = None) -> LaneVersion:
    from auto_trader.strategy_rev import ensure_baseline_rev

    rev = ensure_baseline_rev()
    d = day or datetime.now()
    vid = next_version_for_date(condition_name, d)
    return LaneVersion(
        version_id=vid,
        condition_name=condition_name,
        condition_index=condition_index,
        trade_date=d.strftime("%Y-%m-%d"),
        title=f"{condition_name} 당일매매",
        daily=dict(rev.daily),
        filters=dict(rev.filters),
        changelog="베이스라인(Rev.0)에서 생성",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )


def latest_lane_for_condition(condition_name: str) -> LaneVersion | None:
    versions = list_lane_versions(condition_name)
    if not versions:
        return None

    def sort_key(lv: LaneVersion) -> tuple[str, int]:
        parsed = parse_version_id(lv.version_id)
        if parsed:
            return parsed[0], parsed[1]
        return "000000", 0

    return max(versions, key=sort_key)


def load_active_lanes_map(trade_date: str | None = None) -> dict[str, str]:
    day = trade_date or datetime.now().strftime("%Y-%m-%d")
    if not ACTIVE_LANES_FILE.is_file():
        return {}
    try:
        raw = json.loads(ACTIVE_LANES_FILE.read_text(encoding="utf-8"))
        if raw.get("trade_date") != day:
            return {}
        return dict(raw.get("lanes") or {})
    except (json.JSONDecodeError, OSError):
        return {}


def set_active_lanes(lanes: dict[str, str], trade_date: str | None = None) -> None:
    LANES_DIR.mkdir(parents=True, exist_ok=True)
    day = trade_date or datetime.now().strftime("%Y-%m-%d")
    ACTIVE_LANES_FILE.write_text(
        json.dumps(
            {"trade_date": day, "lanes": lanes, "updated_at": datetime.now().isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def ensure_lane_for_condition(
    condition_name: str,
    condition_index: int,
    day: datetime | None = None,
) -> LaneVersion:
    d = day or datetime.now()
    trade_date = d.strftime("%Y-%m-%d")
    active = load_active_lanes_map(trade_date)
    vid = active.get(condition_name)
    if vid:
        loaded = load_lane_version(vid, condition_name)
        if loaded:
            return loaded

    for lv in list_lane_versions(condition_name):
        if lv.trade_date == trade_date:
            active[condition_name] = lv.version_id
            set_active_lanes(active, trade_date)
            return lv

    parent = latest_lane_for_condition(condition_name)
    if parent and parent.trade_date != trade_date:
        vid = make_version_id(d, 1)
        lv = LaneVersion(
            version_id=vid,
            condition_name=condition_name,
            condition_index=condition_index,
            trade_date=trade_date,
            title=parent.title,
            daily=dict(parent.daily),
            filters=dict(parent.filters),
            parent_version=parent.version_id,
            changelog=f"{parent.version_id} → {vid} (전일 파라미터 계승)",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
    else:
        lv = baseline_lane_version(condition_name, condition_index, d)

    save_lane_version(lv)
    active[condition_name] = lv.version_id
    set_active_lanes(active, trade_date)
    return lv


def tomorrow_version_id() -> str:
    return make_version_id(datetime.now() + timedelta(days=1), 1)
