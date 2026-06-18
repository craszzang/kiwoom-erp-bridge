"""User-configurable stock filter dialog."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from auto_trader import i18n_ko as T
from auto_trader.config import TraderConfig


class FilterSettingsDialog(QDialog):
    def __init__(self, config: TraderConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(T.DLG_FILTER_TITLE)
        self._config = config

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(T.DLG_FILTER_HINT))

        form = QFormLayout()
        self._sell_pct = QDoubleSpinBox()
        self._sell_pct.setRange(0, 100)
        self._sell_pct.setSuffix(" %")
        self._sell_pct.setValue(config.min_sell_balance_pct)
        form.addRow(T.LBL_SELL_PCT, self._sell_pct)

        self._strength = QDoubleSpinBox()
        self._strength.setRange(0, 500)
        self._strength.setDecimals(1)
        self._strength.setValue(config.min_execution_strength)
        form.addRow(T.LBL_EXEC_STRENGTH, self._strength)

        self._pass_only = QCheckBox(T.LBL_PASS_ONLY)
        self._pass_only.setChecked(config.filter_pass_only)
        form.addRow("", self._pass_only)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_to(self, config: TraderConfig) -> None:
        config.min_sell_balance_pct = self._sell_pct.value()
        config.min_execution_strength = self._strength.value()
        config.filter_pass_only = self._pass_only.isChecked()


def edit_filters(config: TraderConfig, parent=None) -> bool:
    dlg = FilterSettingsDialog(config, parent=parent)
    if dlg.exec_() != QDialog.Accepted:
        return False
    dlg.apply_to(config)
    return True
