"""Excel UI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from auto_trader.config import load_config
from auto_trader.excel_ui import run_excel_ui


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiwoom Excel UI")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Fully automated: connect, conditions, BRM, no dialogs",
    )
    args = parser.parse_args()
    cfg = load_config()
    if args.auto:
        cfg.automation.enabled = True
        cfg.automation.auto_brm = True
        cfg.brm.enabled = True
    try:
        return run_excel_ui(config=cfg, auto_mode=args.auto or cfg.automation.enabled)
    except Exception as exc:
        print(f"FATAL: {exc}")
        return 1


if __name__ == "__main__":
    code = main()
    if code != 0 and "--auto" not in sys.argv:
        input("Press Enter to close...")
    raise SystemExit(code)
