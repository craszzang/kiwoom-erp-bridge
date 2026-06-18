"""Excel disguise UI entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from auto_trader.excel_ui import run_excel_ui


def main() -> int:
    try:
        return run_excel_ui()
    except Exception as exc:
        print(f"FATAL: {exc}")
        return 1


if __name__ == "__main__":
    code = main()
    if code != 0:
        input("Press Enter to close...")
    raise SystemExit(code)
