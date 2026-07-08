"""Headless data-collection entry (no Excel UI)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from auto_trader.config import load_config
from auto_trader.headless_runner import run_headless_session


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiwoom headless parallel data collection")
    parser.add_argument("--auto", action="store_true", help="Autonomous session (default)")
    args = parser.parse_args()
    cfg = load_config()
    cfg.automation.enabled = True
    cfg.automation.headless = True
    cfg.daily.enabled = True
    cfg.brm.enabled = False
    try:
        return run_headless_session(cfg)
    except Exception as exc:
        print(f"FATAL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
