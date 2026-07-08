"""Headless parallel lane session — no Excel UI, data collection only."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEventLoop, QObject, QTimer
from PyQt5.QtWidgets import QApplication

from auto_trader.auto_conditions import resolve_parallel_conditions
from auto_trader.auto_log import setup_auto_logging
from auto_trader.auto_loop import is_stop_requested, prepare_session
from auto_trader.condition_picker import ConditionChoice
from auto_trader.config import TraderConfig, load_config, save_config
from auto_trader.kiwoom_api import KiwoomAPI
from auto_trader.lane_session import finalize_parallel_session, prepare_parallel_lanes
from auto_trader.parallel_runner import ParallelDailyRunner
from auto_trader.stock_scanner import ConditionStockScanner

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class HeadlessSession(QObject):
    """Kiwoom + parallel paper lanes without UI widgets."""

    def __init__(self, config: TraderConfig) -> None:
        super().__init__()
        self.config = config
        self.api: KiwoomAPI | None = None
        self.scanner: ConditionStockScanner | None = None
        self._parallel_runner: ParallelDailyRunner | None = None
        self._parallel_lanes = []
        self._selected_conditions: list[ConditionChoice] = []
        self._connected = False

        self._session_timer = QTimer(self)
        self._session_timer.setInterval(30_000)
        self._session_timer.timeout.connect(self._on_session_tick)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_conditions)

        self._connect_timer = QTimer(self)
        self._connect_timer.setSingleShot(True)
        self._connect_timer.timeout.connect(self._connect_and_run)

    def start(self) -> None:
        if getattr(self.config.strategy_auto, "enabled", True):
            prepare_session(self.config)
            save_config(self.config)
        logger.info("headless parallel data collection start")
        self._connect_timer.start(800)

    def _connect_and_run(self) -> None:
        if is_stop_requested():
            QApplication.instance().quit()
            return
        auto = self.config.automation
        try:
            self.api = KiwoomAPI()
        except RuntimeError as exc:
            logger.error("Kiwoom init failed: %s", exc)
            QTimer.singleShot(60_000, self._connect_and_run)
            return

        err = -1
        for attempt in range(1, auto.login_retry_count + 1):
            err = self.api.comm_connect()
            if self.api.is_connected():
                logger.info("kiwoom login ok attempt=%d", attempt)
                break
            logger.warning("kiwoom login fail attempt=%d err=%s", attempt, err)
            if attempt < auto.login_retry_count:
                loop = QEventLoop()
                QTimer.singleShot(auto.login_retry_sec * 1000, loop.quit)
                loop.exec_()

        if not self.api.is_connected():
            logger.error("kiwoom connect failed err=%s", err)
            QTimer.singleShot(60_000, self._connect_and_run)
            return

        accounts = self.api.get_accounts()
        if accounts:
            acc = accounts[0]
            self.config.account_no = acc
            if self.config.use_mock:
                self.config.mock_account_no = acc
            save_config(self.config)

        selected = resolve_parallel_conditions(self.api, self.config)
        if not selected:
            logger.error("no conditions matched — check automation.condition_names in config.yaml")
            if auto.quit_after_session:
                QApplication.instance().quit()
            return

        self._parallel_lanes = prepare_parallel_lanes(self.config, selected)
        self._selected_conditions = selected
        logger.info(
            "parallel lanes: %s",
            [(lv.condition_name, lv.version_id) for lv in self._parallel_lanes],
        )

        self.scanner = ConditionStockScanner(api=self.api, config=self.config)
        self.scanner.bootstrap(conditions=selected)
        self._connected = True

        self._parallel_runner = ParallelDailyRunner(
            api=self.api,
            config=self.config,
            scanner=self.scanner,
            lanes=self._parallel_lanes,
        )
        self._parallel_runner.start()
        logger.info("headless trading active: %s", self._parallel_runner.status_text())

        self._session_timer.start()
        if auto.refresh_conditions_min > 0:
            self._refresh_timer.start(auto.refresh_conditions_min * 60_000)

    def _refresh_conditions(self) -> None:
        if not self._connected or not self.scanner:
            return
        try:
            added = self.scanner.refresh_condition_snapshot()
            if added:
                logger.info("condition refresh +%d", added)
        except Exception as exc:
            logger.warning("condition refresh failed: %s", exc)

    def _on_session_tick(self) -> None:
        if is_stop_requested():
            self._end_session("stop flag")
            return
        end_t = self.config.daily.t_force_flat
        if datetime.now().time() >= end_t:
            self._end_session("session end")

    def _end_session(self, reason: str) -> None:
        logger.info("headless session end: %s", reason)
        self._session_timer.stop()
        self._refresh_timer.stop()
        if self._parallel_runner:
            self._parallel_runner.stop()
            cond_names = [c.name for c in self._selected_conditions]
            finalize_parallel_session(self.config, self._parallel_runner, cond_names)
        if self.scanner:
            self.scanner._stop_conditions()
        if self.config.automation.quit_after_session:
            QApplication.instance().quit()


def run_headless_session(config: TraderConfig | None = None) -> int:
    setup_auto_logging(config.log_level if config else "INFO")
    cfg = config or load_config()
    cfg.automation.enabled = True
    cfg.daily.enabled = True
    cfg.brm.enabled = False
    if getattr(cfg.strategy_auto, "parallel_lanes", True):
        cfg.strategy_auto.parallel_lanes = True

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    session = HeadlessSession(cfg)
    session.start()
    return app.exec_()
