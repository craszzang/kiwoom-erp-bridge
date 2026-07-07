"""Strategy revision registry (Rev.0, Rev.1, ...)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from auto_trader.brm_params import BrmParams
from auto_trader.daily_params import DailyParams

logger = logging.getLogger(__name__)

STRATEGIES_DIR = Path(__file__).resolve().parent.parent / "strategies"
ACTIVE_FILE = STRATEGIES_DIR / "active.json"


@dataclass
class StrategyRev:
    rev_id: str
    title: str
    description: str
    created_at: str
    brm: dict[str, Any] = field(default_factory=dict)
    daily: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, Any] = field(default_factory=dict)
    condition_keywords: list[str] = field(default_factory=list)
    changelog: str = ""
    parent_rev: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StrategyRev":
        return cls(
            rev_id=str(raw.get("rev_id", "Rev.0")),
            title=str(raw.get("title", "")),
            description=str(raw.get("description", "")),
            created_at=str(raw.get("created_at", "")),
            brm=dict(raw.get("brm") or {}),
            daily=dict(raw.get("daily") or {}),
            filters=dict(raw.get("filters") or {}),
            condition_keywords=list(raw.get("condition_keywords") or []),
            changelog=str(raw.get("changelog", "")),
            parent_rev=str(raw.get("parent_rev", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rev_file(rev_id: str) -> Path:
    safe = rev_id.replace(".", "_").lower()
    return STRATEGIES_DIR / f"{safe}.json"


def list_revs() -> list[StrategyRev]:
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    out: list[StrategyRev] = []
    for path in sorted(STRATEGIES_DIR.glob("rev_*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            out.append(StrategyRev.from_dict(raw))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("skip rev file %s: %s", path.name, exc)
    return out


def load_rev(rev_id: str) -> StrategyRev | None:
    path = rev_file(rev_id)
    if not path.is_file():
        return None
    return StrategyRev.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_rev(rev: StrategyRev) -> Path:
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    path = rev_file(rev.rev_id)
    path.write_text(json.dumps(rev.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_active_rev_id() -> str:
    if not ACTIVE_FILE.is_file():
        return "Rev.0"
    try:
        raw = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
        return str(raw.get("active_rev", "Rev.0"))
    except (json.JSONDecodeError, OSError):
        return "Rev.0"


def set_active_rev(rev_id: str) -> None:
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_FILE.write_text(
        json.dumps({"active_rev": rev_id, "updated_at": datetime.now().isoformat()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_active_rev() -> StrategyRev:
    rev_id = get_active_rev_id()
    rev = load_rev(rev_id)
    if rev:
        return rev
    baseline = ensure_baseline_rev()
    set_active_rev(baseline.rev_id)
    return baseline


def next_rev_id() -> str:
    revs = list_revs()
    if not revs:
        return "Rev.1"
    nums: list[int] = []
    for r in revs:
        tail = r.rev_id.replace("Rev.", "")
        if tail.isdigit():
            nums.append(int(tail))
    return f"Rev.{max(nums, default=0) + 1}"


def ensure_baseline_rev() -> StrategyRev:
    """Rev.0 — morning scalping baseline tuned for catch mock."""
    existing = load_rev("Rev.0")
    if existing:
        return existing
    rev = StrategyRev(
        rev_id="Rev.0",
        title="캐치 당일매매 베이스라인",
        description=(
            "조건식(캐치) + 매도잔량>매수 + 체결강도 진입. "
            "고점 추적 매도·익절·손절·15:20 전량청산. 당일 매수·당일 매도."
        ),
        created_at=datetime.now().strftime("%Y-%m-%d"),
        daily={
            "enabled": True,
            "paper_only": True,
            "session_start": "09:05",
            "session_end": "15:20",
            "entry_cutoff": "14:30",
            "force_flat": "15:20",
            "min_sell_balance_pct": 52.0,
            "min_execution_strength": 110.0,
            "exit_strength_below": 95.0,
            "take_profit_pct": 2.0,
            "stop_loss_pct": 2.5,
            "trail_from_peak_pct": 0.6,
            "min_profit_to_trail_pct": 0.35,
            "max_positions": 3,
            "base_qty": 1,
            "max_symbols": 40,
            "rsi_exit_high": 72.0,
            "log_signals": True,
        },
        brm={"enabled": False},
        filters={
            "min_sell_balance_pct": 52.0,
            "min_execution_strength": 110.0,
            "filter_pass_only": True,
        },
        condition_keywords=["급등", "거래량", "돌파", "모멘텀", "체결"],
        changelog="초기 베이스라인 — 당일매매·고점추적(Rev.0)",
    )
    save_rev(rev)
    return rev


def apply_rev_to_config(rev: StrategyRev, config: Any) -> None:
    """Merge rev params into TraderConfig (in-place)."""
    if rev.daily:
        base = config.daily.to_dict()
        base.update(rev.daily)
        config.daily = DailyParams.from_dict(base)
        config.daily.enabled = True
        config.daily.paper_only = True
        config.brm.enabled = False
        if "min_sell_balance_pct" in rev.daily:
            v = float(rev.daily["min_sell_balance_pct"])
            config.min_sell_balance_pct = v
            config.daily.min_sell_balance_pct = v
        if "min_execution_strength" in rev.daily:
            v = float(rev.daily["min_execution_strength"])
            config.min_execution_strength = v
            config.daily.min_execution_strength = v
    elif rev.brm:
        base = config.brm.to_dict()
        base.update(rev.brm)
        config.brm = BrmParams.from_dict(base)
        config.brm.enabled = True
        config.brm.paper_only = True
    if rev.filters:
        if "min_sell_balance_pct" in rev.filters:
            config.min_sell_balance_pct = float(rev.filters["min_sell_balance_pct"])
            config.brm.min_sell_balance_pct = config.min_sell_balance_pct
            config.daily.min_sell_balance_pct = config.min_sell_balance_pct
        if "min_execution_strength" in rev.filters:
            config.min_execution_strength = float(rev.filters["min_execution_strength"])
            config.brm.min_execution_strength = config.min_execution_strength
            config.daily.min_execution_strength = config.min_execution_strength
        if "filter_pass_only" in rev.filters:
            config.filter_pass_only = bool(rev.filters["filter_pass_only"])
    if rev.condition_keywords and config.automation:
        names = list(config.automation.condition_names or [])
        for kw in rev.condition_keywords:
            if kw not in names:
                names.append(kw)
        config.automation.condition_names = names
