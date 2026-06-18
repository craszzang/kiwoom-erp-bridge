"""Visible startup splash for remote client."""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from auto_trader import i18n_ko as T


class RemoteStartupSplash(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(T.REMOTE_SPLASH_TITLE)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(460, 140)
        lay = QVBoxLayout(self)
        self._label = QLabel(T.REMOTE_SPLASH_START)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._label)

    def set_status(self, text: str) -> None:
        self._label.setText(text)
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def pulse(self, step: Callable[[], None]) -> None:
        step()
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.processEvents()
