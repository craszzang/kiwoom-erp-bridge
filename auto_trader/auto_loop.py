"""Autonomous mock-trading loop: strategy prep, finalize, evolve."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from auto_trader.session_report import book_to_session_dict, format_telegram_message, save_session_report
from auto_trader.strategy_optimizer import maybe_evolve_and_activate
from auto_trader.strategy_rev import apply_rev_to_config, ensure_baseline_rev, load_active_rev, load_rev
from auto_trader.telegram_notify import load_telegram_config, send_session_report

if TYPE_CHECKING:
    from auto_trader.brm_runner import BrmPaperRunner
    from auto_trader.config import TraderConfig
    from auto_trader.daily_runner import DailyRunner

TradingRunner = "BrmPaperRunner | DailyRunner"

logger = logging.getLogger(__name__)

STOP_FLAG = Path.home() / "AppData" / "Local" / "kiwoom-trader" / "autonomous_stop.flag"
RUN_FLAG = Path.home() / "AppData" / "Local" / "kiwoom-trader" / "autonomous_run.flag"


def is_stop_requested() -> bool:
    return STOP_FLAG.is_file()


def request_stop() -> None:
    STOP_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STOP_FLAG.write_text(datetime.now().isoformat(), encoding="utf-8")
    logger.info("autonomous stop requested")


def clear_stop() -> None:
    if STOP_FLAG.is_file():
        STOP_FLAG.unlink()


def prepare_session(config: "TraderConfig") -> str:
    """Load active strategy rev and apply to config. Returns rev_id."""
    ensure_baseline_rev()
    rev = load_active_rev()
    apply_rev_to_config(rev, config)
    RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
    RUN_FLAG.write_text(rev.rev_id, encoding="utf-8")
    logger.info("session prepared with %s — %s", rev.rev_id, rev.title)
    return rev.rev_id


def finalize_session(
    config: "TraderConfig",
    runner: "BrmPaperRunner | DailyRunner | None",
    condition_names: list[str] | None = None,
) -> None:
    """Save report, evolve strategy, send Telegram."""
    if not runner:
        logger.warning("finalize: no trading runner")
        return
    rev = load_active_rev()
    names = condition_names or []
    if config.condition_name and config.condition_name not in names:
        names.insert(0, config.condition_name)

    session = book_to_session_dict(
        runner.engine.book,
        rev_id=rev.rev_id,
        condition_names=names,
    )
    save_session_report(session)

    auto_evolve = getattr(config, "strategy_auto", None)
    evolve_enabled = True if auto_evolve is None else bool(getattr(auto_evolve, "auto_evolve", True))
    if evolve_enabled:
        new_rev = maybe_evolve_and_activate(rev, session, auto_activate=True)
        if new_rev.rev_id != rev.rev_id:
            session["next_rev_changelog"] = new_rev.changelog
            session["next_rev_id"] = new_rev.rev_id
            save_session_report(session)

    tg_cfg = load_telegram_config()
    if tg_cfg.enabled:
        msg = format_telegram_message(session, rev_title=rev.title)
        if session.get("next_rev_id"):
            msg += f"\n\n🆕 활성 전략 → <b>{session['next_rev_id']}</b>"
        ok = send_session_report(msg)
        logger.info("telegram report sent=%s", ok)
    else:
        logger.warning("telegram not configured — copy config.telegram.example.yaml")
