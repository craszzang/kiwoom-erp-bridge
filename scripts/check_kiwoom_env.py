"""Kiwoom environment diagnostic."""

from __future__ import annotations

import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from PyQt5.QtWidgets import QApplication

OCX = Path(r"C:\OpenAPI\khopenapi.ocx")


def main() -> int:
    bits = struct.calcsize("P") * 8
    print("=== Kiwoom check ===")
    print(f"Python: {sys.executable}")
    print(f"Arch: {bits}-bit")
    print(f"OCX: {OCX.exists()} ({OCX})")

    if bits != 32:
        print("\nFAIL: 32-bit Python required.")
        print("Run setup_env.bat then use .venv32")
        return 1

    reg = subprocess.run(
        ["reg", "query", r"HKCR\KHOPENAPI.KHOpenAPICtrl.1"],
        capture_output=True,
        text=True,
        encoding="cp949",
        errors="ignore",
    )
    print(f"COM registry: {'OK' if reg.returncode == 0 else 'MISSING'}")

    app = QApplication([])
    try:
        from auto_trader.kiwoom_api import KiwoomAPI

        KiwoomAPI()
        print("\nOK: Kiwoom OCX loaded successfully.")
        return 0
    except Exception as exc:
        print(f"\nFAIL: {exc}")
        print("\nNext: register_kiwoom_ocx_admin.bat (Run as admin)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
