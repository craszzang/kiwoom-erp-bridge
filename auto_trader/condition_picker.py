"""Kiwoom condition formula picker dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from auto_trader import i18n_ko as T
from auto_trader.kiwoom_api import KiwoomAPI


@dataclass(frozen=True)
class ConditionChoice:
    index: int
    name: str


class ConditionPickerDialog(QDialog):
    def __init__(self, conditions: list[ConditionChoice], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(T.DLG_COND_TITLE)
        self.resize(480, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(T.DLG_COND_HINT))

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        for cond in conditions:
            item = QListWidgetItem(f"[{cond.index}] {cond.name}")
            item.setData(Qt.UserRole, cond)
            self._list.addItem(item)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox()
        ok_btn = buttons.addButton(T.DLG_COND_OK, QDialogButtonBox.AcceptRole)
        skip_btn = buttons.addButton(T.DLG_COND_SKIP, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        ok_btn.clicked.connect(self._accept_selected)
        skip_btn.clicked.connect(self._accept_skip)
        layout.addWidget(buttons)

        self._result: list[ConditionChoice] | None = None

    def _accept_selected(self) -> None:
        items = self._list.selectedItems()
        if not items:
            QMessageBox.information(self, T.DLG_COND_TITLE, T.DLG_COND_EMPTY)
            return
        self._result = [item.data(Qt.UserRole) for item in items]
        self.accept()

    def _accept_skip(self) -> None:
        self._result = []
        self.accept()

    @property
    def choices(self) -> list[ConditionChoice]:
        return self._result or []


def load_conditions_from_api(api: KiwoomAPI) -> list[ConditionChoice]:
    return [ConditionChoice(index=idx, name=name) for idx, name in api.get_condition_name_list()]


def pick_conditions(api: KiwoomAPI, parent=None) -> list[ConditionChoice] | None:
    try:
        conditions = load_conditions_from_api(api)
    except Exception as exc:
        QMessageBox.warning(parent, T.DLG_COND_TITLE, T.DLG_COND_LOAD_FAIL.format(err=exc))
        return []

    if not conditions:
        QMessageBox.information(parent, T.DLG_COND_TITLE, T.DLG_COND_NONE)
        return []

    dlg = ConditionPickerDialog(conditions, parent=parent)
    if dlg.exec_() != QDialog.Accepted:
        return None
    return dlg.choices
