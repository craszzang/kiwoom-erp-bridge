# -*- coding: utf-8 -*-
"""Show Kiwoom login dialog and keep process alive."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from PyQt5.QtWidgets import QApplication, QMessageBox

from auto_trader.kiwoom_api import KiwoomAPI


def main() -> int:
    app = QApplication(sys.argv)
    try:
        api = KiwoomAPI()
    except RuntimeError as exc:
        QMessageBox.critical(None, "Kiwoom", str(exc))
        return 1

    err = api.comm_connect()
    if api.is_connected():
        name = api.get_login_info("USER_NAME")
        accs = ", ".join(api.get_accounts()) or "-"
        QMessageBox.information(
            None,
            "Login OK",
            f"Connected.\n\nUser: {name}\nAccount: {accs}",
        )
        return 0

    detail = KiwoomAPI.login_error_text(err)
    QMessageBox.warning(None, "Login failed", detail)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
