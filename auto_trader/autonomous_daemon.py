"""Infinite weekday autonomous mock-trading daemon."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auto_trader.auto_loop import clear_stop, is_stop_requested, prepare_session
from auto_trader.auto_log import setup_auto_logging
from auto_trader.config import load_config, save_config

try:
    from scripts.host_git_pull import git_pull_ff
except ImportError:
    _scripts = ROOT / "scripts"
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))
    from host_git_pull import git_pull_ff

logger = logging.getLogger(__name__)

PY = ROOT / ".venv32" / "Scripts" / "python.exe"
EXCEL_MAIN = ROOT / "auto_trader" / "excel_main.py"
START_HM = (8, 45)
SESSION_END_HM = (15, 25)


def _is_weekday(now: datetime | None = None) -> bool:
    return (now or datetime.now()).weekday() < 5


def _wait_until(hour: int, minute: int) -> None:
    while not is_stop_requested():
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target:
            return
        sleep_sec = min(60, max(5, (target - now).total_seconds()))
        logger.info("wait until %02d:%02d (%ds)", hour, minute, int(sleep_sec))
        time.sleep(sleep_sec)


def _wait_next_trading_morning() -> None:
    while not is_stop_requested():
        now = datetime.now()
        if _is_weekday(now) and now.time() < dt_time(*START_HM):
            _wait_until(*START_HM)
            return
        tomorrow = (now + timedelta(days=1)).replace(hour=START_HM[0], minute=START_HM[1], second=0)
        while tomorrow.weekday() >= 5:
            tomorrow += timedelta(days=1)
        sleep_sec = min(3600, max(30, (tomorrow - now).total_seconds()))
        logger.info("next session ~%s (sleep %ds)", tomorrow.strftime("%Y-%m-%d %H:%M"), int(sleep_sec))
        time.sleep(sleep_sec)
        if _is_weekday() and datetime.now().time() >= dt_time(*START_HM):
            return


def _run_trading_session() -> int:
    ok, msg = git_pull_ff(ROOT)
    if ok:
        logger.info("github sync: %s", msg.splitlines()[-1] if msg else "ok")
    else:
        logger.warning("github sync skipped/failed: %s", msg)
    cfg = load_config()
    rev_id = prepare_session(cfg)
    save_config(cfg)
    logger.info("starting session rev=%s", rev_id)
    py = str(PY) if PY.is_file() else sys.executable
    env = dict(**__import__("os").environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [py, "-X", "utf8", str(EXCEL_MAIN), "--auto"],
        cwd=r"C:\OpenAPI",
        env=env,
    )
    return int(proc.returncode)


def main() -> int:
    setup_auto_logging("INFO")
    logger.info("autonomous daemon start (stop flag=%s)", is_stop_requested())
    if not PY.is_file():
        logger.error("missing .venv32 — run setup_env.bat first")
        return 1
    ok, msg = git_pull_ff(ROOT)
    logger.info("startup github sync: %s", msg if msg else ("ok" if ok else "skipped"))

    while not is_stop_requested():
        if not _is_weekday():
            logger.info("weekend — sleep 1h")
            time.sleep(3600)
            continue
        now = datetime.now()
        if now.time() < dt_time(*START_HM):
            _wait_until(*START_HM)
        if is_stop_requested():
            break
        if now.time() >= dt_time(*SESSION_END_HM):
            _wait_next_trading_morning()
            continue
        code = _run_trading_session()
        logger.info("session finished exit=%d", code)
        _wait_next_trading_morning()

    logger.info("autonomous daemon stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
