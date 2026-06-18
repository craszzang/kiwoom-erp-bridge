"""Host entry: Kiwoom login + bridge server (no Excel UI on host)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget

from auto_trader import i18n_ko as T
from auto_trader.bridge_protocol import DEFAULT_BRIDGE_PORT, DEFAULT_HTTP_PORT
from auto_trader.bridge_server import BridgeController
from auto_trader.config import TraderConfig, load_config, save_config
from auto_trader.kiwoom_api import KiwoomAPI
from auto_trader.stock_scanner import ConditionStockScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class BridgeHostWindow(QWidget):
    def __init__(self, config: TraderConfig) -> None:
        super().__init__()
        self.config = config
        self.setWindowTitle("키움 브릿지 서버 (호스트)")
        self.resize(520, 200)
        lay = QVBoxLayout(self)
        self._label = QLabel("브릿지 시작 중...")
        lay.addWidget(self._label)

        self.api = KiwoomAPI()
        self.bridge = BridgeController(self.api, config, ROOT)
        self.scanner = ConditionStockScanner(
            api=self.api,
            config=config,
            on_state_change=lambda: None,
        )
        self.bridge.attach_scanner(self.scanner)
        self.api.register_chejan_callback(self.bridge.on_chejan)

        ws_port = int(getattr(config, "bridge_port", DEFAULT_BRIDGE_PORT) or DEFAULT_BRIDGE_PORT)
        http_port = int(getattr(config, "bridge_http_port", DEFAULT_HTTP_PORT) or DEFAULT_HTTP_PORT)
        self.bridge.start(ws_port=ws_port, http_port=http_port)

        self._label.setText(
            f"WS {ws_port} / HTTP {http_port}\n"
            "1) 키움 로그인 창에서 모의투자(캐치) 로그인\n"
            "2) 고객 PC에서 재고실적_집계-원격.bat 실행"
        )
        QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_ERP_BODY)
        self._login()

    def _login(self) -> None:
        err = self.api.comm_connect()
        if err != 0 or not self.api.is_connected():
            detail = KiwoomAPI.login_error_text(err)
            QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_CONN_FAIL_FMT.format(detail=detail))
            return

        accounts = self.api.get_accounts()
        if accounts:
            acc = accounts[0]
            if self.config.use_mock:
                self.config.mock_account_no = acc
            self.config.account_no = acc
            save_config(self.config)

        QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_ACCOUNT_PW_HINT)
        self.api.show_account_password_window()
        self._label.setText(self._label.text() + f"\n\n연결됨 | 계좌 {accounts[0] if accounts else '-'}")


def main() -> int:
    config = load_config()
    app = QApplication.instance() or QApplication([])
    win = BridgeHostWindow(config=config)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
