# -*- coding: utf-8 -*-
"""??? ?????? ??????."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from PyQt5.QtWidgets import QApplication, QMessageBox

from auto_trader.config import MOCK_LOGIN_HINT, load_config, save_config
from auto_trader.kiwoom_api import KiwoomAPI
from auto_trader.strategy import SimpleMomentumStrategy


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _warn_mock_login(config) -> None:
    acc = config.mock_account_no or config.account_no
    extra = f"\n\n???? ????: {acc}" if acc else ""
    QMessageBox.information(None, "��????? ?��???", MOCK_LOGIN_HINT + extra)


def main() -> int:
    config = load_config()
    setup_logging(config.log_level)
    logger = logging.getLogger("main")

    app = QApplication.instance() or QApplication(sys.argv)
    api = KiwoomAPI()

    if config.use_mock:
        _warn_mock_login(config)

    logger.info("??? ?��??? ??? ?????...")
    err = api.comm_connect()
    if err != 0:
        logger.error("?��??? ???? err_code=%s", err)
        return 1

    server = api.get_login_info("GetServerGubun")
    is_mock = server == "1"
    user_id = api.get_login_info("USER_ID")
    user_name = api.get_login_info("USER_NAME")
    accounts = api.get_accounts()
    logger.info(
        "?��??? ????: %s(%s), ????=%s, ???? %s",
        user_name,
        user_id,
        "????" if is_mock else "????",
        accounts,
    )

    if config.use_mock and not is_mock:
        logger.error("????? ?��??��?. ��?????/???????? ???? ?? ?? ??? ?��????????.")
        return 2

    if accounts:
        api_acc = accounts[0]
        if config.use_mock:
            config.mock_account_no = api_acc
        else:
            config.real_account_no = api_acc
        config.account_no = config.active_account_no or api_acc
        save_config(config)
        logger.info("???��?? ???: ????=%s, API=%s", config.account_no, api_acc)

    strategy = SimpleMomentumStrategy(api=api, config=config)
    strategy.bootstrap()

    logger.info("?????? ???? ???? ?? (????: Ctrl+C ??? ? ???)")
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
