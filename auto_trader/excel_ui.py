"""Excel-like disguise dashboard with trading controls."""

from __future__ import annotations

import threading
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QShortcut,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from auto_trader import i18n_ko as T
from auto_trader.condition_picker import ConditionChoice, pick_conditions
from auto_trader.config import TraderConfig, load_config, save_config
from auto_trader.filter_dialog import edit_filters
from auto_trader.kiwoom_api import KiwoomAPI
from auto_trader.positions import PositionBook
from auto_trader.stock_scanner import ConditionStockScanner, StockQuote

if False:  # TYPE_CHECKING
    from auto_trader.remote_client import RemoteBridgeClient

DATA_START_ROW = 4
HEADER_ROW = 3
FONT = "Malgun Gothic"
LITE_DISPLAY_CAP = 150
TRADE_WIDGET_COLS = (
    T.COL_QTY,
    T.COL_MKT_BUY,
    T.COL_MKT_SELL,
    T.COL_LMT_BUY,
    T.COL_LMT_SELL,
)


def row_color_for_index(idx: int) -> str:
    total = sum(n for _, n in T.ROW_COLOR_BLOCKS)
    pos = idx % total
    acc = 0
    for color, count in T.ROW_COLOR_BLOCKS:
        acc += count
        if pos < acc:
            return color
    return T.ROW_COLOR_BLOCKS[0][0]


def pnl_color(value: float) -> QColor:
    if value > 0:
        return QColor(T.PNL_PLUS)
    if value < 0:
        return QColor(T.PNL_MINUS)
    return QColor("#000000")


class ExcelDisguiseWindow(QMainWindow):
    def __init__(self, config: TraderConfig, bridge: "RemoteBridgeClient | None" = None) -> None:
        super().__init__()
        self.api: KiwoomAPI | None = None
        self.config = config
        self._bridge = bridge
        self._remote_mode = bridge is not None or config.bridge_role == "client"
        self.scanner: ConditionStockScanner | None = None
        self.positions = PositionBook()
        self._connected = False
        self._selected_conditions: list[ConditionChoice] = []
        self._stock_start_row = DATA_START_ROW + len(T.DECOY_ROWS)
        self._code_row: dict[str, int] = {}
        self._qty_spins: dict[str, QSpinBox] = {}
        self._rebuilding_grid = False
        self._grid_refresh_timer = QTimer(self)
        self._grid_refresh_timer.setSingleShot(True)
        self._grid_refresh_timer.setInterval(120)
        self._grid_refresh_timer.timeout.connect(self._apply_scanner_update)

        self.setWindowTitle(T.WIN_TITLE)
        self.resize(1680, 800)
        self._build_ui()

        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_status)
        self._clock.start(30_000)

        sync_shortcut = QShortcut(QKeySequence("F5"), self)
        sync_shortcut.activated.connect(self._start_sync)
        QTimer.singleShot(500, self._prompt_connect)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._ribbon())
        root.addWidget(self._formula_bar())
        root.addWidget(self._filter_bar())
        root.addWidget(self._sheet_area(), stretch=1)
        root.addWidget(self._sheet_tabs())
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._tick_status()
        self._menu_bar()

    def _menu_bar(self) -> None:
        mb = self.menuBar()
        for name in T.MENU_NAMES:
            menu = mb.addMenu(name)
            if name.startswith("\ud30c\uc77c"):
                act = QAction("\uc800\uc7a5", self)
                act.triggered.connect(lambda: self._status.showMessage(T.MSG_SAVE_OK, 2000))
                menu.addAction(act)
            if name.startswith("\ub370\uc774\ud130"):
                act = QAction("\uc0c8\ub85c\uace0\uce68 (F5)", self)
                act.setShortcut("F5")
                act.triggered.connect(self._start_sync)
                menu.addAction(act)
                menu.addAction(T.MENU_COND_PICK, self._pick_conditions)
                menu.addAction(T.MENU_FILTER, self._edit_filters)
                menu.addAction(T.MENU_ACCOUNT_PW, self._register_account_password)

    def _ribbon(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(72)
        bar.setStyleSheet("background:#217346;")
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(8, 4, 8, 4)
        tabs = QHBoxLayout()
        for i, t in enumerate(T.RIBBON_TABS):
            lbl = QLabel(t)
            lbl.setStyleSheet(
                f"color:white; padding:4px 12px; background:{'#1a5c38' if i == 1 else 'transparent'};"
            )
            tabs.addWidget(lbl)
        tabs.addStretch()
        lay.addLayout(tabs)
        tools = QHBoxLayout()
        for text in T.TOOL_BTNS:
            btn = QToolButton()
            btn.setText(text)
            btn.setStyleSheet(
                "QToolButton { background:#f3f3f3; border:1px solid #ccc; "
                "padding:4px 8px; margin:1px; font-size:11px; }"
            )
            if text == "\uc0c8\ub85c\uace0\uce68":
                btn.clicked.connect(self._start_sync)
            tools.addWidget(btn)
        tools.addStretch()
        lay.addLayout(tools)
        return bar

    def _formula_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(28)
        bar.setStyleSheet("background:#f3f3f3; border-bottom:1px solid #d4d4d4;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.addWidget(QLabel("A1"))
        self._formula = QLineEdit(T.FORMULA_TITLE)
        self._formula.setReadOnly(True)
        self._formula.setStyleSheet("background:white; border:1px solid #ccc; padding:2px;")
        lay.addWidget(self._formula, stretch=1)
        return bar

    def _filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(34)
        bar.setStyleSheet("background:#f3f3f3; border-bottom:1px solid #d4d4d4;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 2, 8, 2)

        lay.addWidget(QLabel(T.LBL_FILTER_BAR_SELL))
        self._sell_spin = QDoubleSpinBox()
        self._sell_spin.setRange(0, 100)
        self._sell_spin.setSuffix(" %")
        self._sell_spin.setValue(self.config.min_sell_balance_pct)
        self._sell_spin.setFixedWidth(80)
        lay.addWidget(self._sell_spin)

        lay.addSpacing(12)
        lay.addWidget(QLabel(T.LBL_FILTER_BAR_STRENGTH))
        self._strength_spin = QDoubleSpinBox()
        self._strength_spin.setRange(0, 500)
        self._strength_spin.setDecimals(1)
        self._strength_spin.setValue(self.config.min_execution_strength)
        self._strength_spin.setFixedWidth(80)
        lay.addWidget(self._strength_spin)

        self._pass_only_chk = QCheckBox(T.LBL_PASS_ONLY)
        self._pass_only_chk.setChecked(self.config.filter_pass_only)
        lay.addWidget(self._pass_only_chk)

        apply_btn = QPushButton(T.BTN_FILTER_APPLY)
        apply_btn.clicked.connect(self._apply_filter_bar)
        lay.addWidget(apply_btn)
        lay.addStretch()
        return bar

    def _apply_filter_bar(self) -> None:
        self.config.min_sell_balance_pct = self._sell_spin.value()
        self.config.min_execution_strength = self._strength_spin.value()
        self.config.filter_pass_only = self._pass_only_chk.isChecked()
        save_config(self.config)
        if self._meta_item:
            self._meta_item.setText(self._meta_text())
        self._code_row.clear()
        self._qty_spins.clear()
        self.refresh_grid(full_rebuild=True)

    def _sheet_area(self) -> QWidget:
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        ncol = len(T.COL_HEADERS)
        self._table = QTableWidget(50, ncol)
        self._table.setHorizontalHeaderLabels([chr(65 + i) for i in range(ncol)])
        self._table.horizontalHeader().setStyleSheet(
            f"QHeaderView::section {{ background:{T.HEADER_BG}; color:{T.HEADER_FG}; "
            "border:1px solid #333; padding:3px; font-weight:bold; }"
        )
        self._table.verticalHeader().setVisible(False)

        title = QTableWidgetItem(T.SHEET_TITLE)
        title.setFont(QFont(FONT, 11, QFont.Bold))
        self._table.setItem(0, 0, title)
        self._table.setSpan(0, 0, 1, ncol)

        self._meta_item = QTableWidgetItem(self._meta_text())
        self._table.setItem(1, 0, self._meta_item)
        self._table.setSpan(1, 0, 1, ncol)

        for c, h in enumerate(T.COL_HEADERS):
            cell = QTableWidgetItem(h)
            cell.setBackground(QColor(T.HEADER_BG))
            cell.setForeground(QColor(T.HEADER_FG))
            cell.setFont(QFont(FONT, 9, QFont.Bold))
            self._table.setItem(HEADER_ROW, c, cell)

        row = DATA_START_ROW
        for i, d in enumerate(T.DECOY_ROWS):
            bg = QColor(row_color_for_index(i))
            vals = list(d)
            while len(vals) < ncol:
                vals.insert(8, "")
            for c, val in enumerate(vals[:ncol]):
                item = QTableWidgetItem(val)
                item.setBackground(bg)
                self._table.setItem(row, c, item)
            row += 1

        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setStyleSheet(
            f"QTableWidget {{ gridline-color:#808080; font-family:'{FONT}'; font-size:10pt; }}"
            "QTableWidget::item:selected { background:#cce8cf; color:black; }"
        )
        widths = [82, 82, 100, 40, 128, 72, 64, 68, 78, 84, 48, 64, 64, 104, 104, 72, 50, 72, 50, 92, 50]
        for i, w in enumerate(widths[:ncol]):
            self._table.setColumnWidth(i, w)
        lay.addWidget(self._table, stretch=1)
        return wrap

    def _meta_text(self) -> str:
        return T.META_FMT.format(
            date=datetime.now().strftime("%Y-%m-%d"),
            sell_pct=self.config.min_sell_balance_pct,
            strength=self.config.min_execution_strength,
        )

    def _sheet_tabs(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(26)
        bar.setStyleSheet("background:#f3f3f3; border-top:1px solid #d4d4d4;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(6, 0, 6, 0)
        for i, name in enumerate(T.SHEET_TABS):
            lbl = QLabel(f"  {name}  ")
            lbl.setStyleSheet(
                f"background:{'white' if i == 1 else '#e8e8e8'}; "
                "border:1px solid #bbb; padding:2px 8px; font-size:10pt;"
            )
            lay.addWidget(lbl)
        lay.addStretch()
        return bar

    def _set_cell(self, row: int, col: int, text: str, bg: QColor, fg: QColor | None = None) -> None:
        item = self._table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            self._table.setItem(row, col, item)
        item.setText(text)
        item.setBackground(bg)
        if fg is not None:
            item.setForeground(fg)
        else:
            item.setForeground(QColor("#000000"))

    def _make_btn(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet("font-size:9pt; padding:2px 4px;")
        btn.clicked.connect(callback)
        return btn

    def _make_limit_widget(self, code: str, is_buy: bool) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(2)
        edit = QLineEdit()
        edit.setPlaceholderText(T.PH_LIMIT_PRICE)
        edit.setMaximumWidth(58)
        btn = self._make_btn(
            T.BTN_LMT_BUY if is_buy else T.BTN_LMT_SELL,
            lambda _=False, c=code, b=is_buy, e=edit: self._order_limit(c, b, e),
        )
        lay.addWidget(edit)
        lay.addWidget(btn)
        return w

    def _attach_qty_widget(self, row: int, code: str) -> None:
        spin = QSpinBox()
        spin.setRange(1, 999_999)
        spin.setValue(self.config.order_qty)
        spin.setMaximumWidth(52)
        spin.valueChanged.connect(lambda _v, c=code: self._on_qty_changed(c))
        self._table.setCellWidget(row, T.COL_QTY, spin)
        self._qty_spins[code] = spin

    def _on_qty_changed(self, code: str) -> None:
        row = self._code_row.get(code)
        quote = self._quote(code)
        if row is not None:
            self._update_est_amount_cell(row, code, quote.price if quote else 0)

    def _get_qty(self, code: str) -> int:
        spin = self._qty_spins.get(code)
        return spin.value() if spin else self.config.order_qty

    def _update_est_amount_cell(self, row: int, code: str, price: int) -> None:
        bg = QColor(row_color_for_index(row - self._stock_start_row))
        qty = self._get_qty(code)
        if price > 0 and qty > 0:
            text = T.EST_AMOUNT_FMT.format(amount=price * qty)
        else:
            text = "-"
        self._set_cell(row, T.COL_EST_AMOUNT, text, bg)

    def _attach_trade_widgets(self, row: int, code: str) -> None:
        self._table.setCellWidget(row, T.COL_MKT_BUY, self._make_btn(T.BTN_MKT_BUY, lambda: self._order_market(code, True)))
        self._table.setCellWidget(
            row, T.COL_MKT_SELL, self._make_btn(T.BTN_MKT_SELL, lambda: self._order_market(code, False))
        )
        self._table.setCellWidget(row, T.COL_LMT_BUY, self._make_limit_widget(code, True))
        self._table.setCellWidget(row, T.COL_LMT_SELL, self._make_limit_widget(code, False))

    def _displayed_quotes(self) -> list[StockQuote]:
        if not self.scanner:
            return []
        return self.scanner.display_quotes()

    def _displayed_codes(self) -> set[str]:
        return {q.code for q in self._displayed_quotes()}

    def _paint_row_cells(self, row: int, quote: StockQuote, color_idx: int) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        bg = QColor(row_color_for_index(color_idx))

        state = quote.filter_state(
            self.config.min_sell_balance_pct,
            self.config.min_execution_strength,
        )
        if state == "pass":
            status = T.NOTE_MATCH
        elif state == "wait":
            status = T.NOTE_WAIT
        else:
            status = T.NOTE_FAIL

        total = quote.sell_total + quote.buy_total
        sell_text = (
            T.SELL_PCT_FMT.format(pct=quote.sell_balance_pct, sell=quote.sell_total, total=total)
            if total > 0
            else "-"
        )
        strength_text = f"{quote.execution_strength:.1f}" if quote.execution_strength else "-"
        price_text = f"{quote.price:,}" if quote.price else "-"

        base_vals = [
            f"{today}-{quote.code[-4:]}",
            today,
            quote.code,
            "1",
            quote.name or T.NOTE_LOADING,
            "\uc2e4\uc2dc\uac04",
            status,
            price_text,
        ]
        for c, val in enumerate(base_vals):
            self._set_cell(row, c, val, bg)
            if c == T.COL_VENDOR:
                item = self._table.item(row, c)
                if item:
                    item.setFont(QFont(FONT, 10, QFont.Bold))

        self._set_cell(row, T.COL_SELL_BAL, sell_text, bg)
        self._set_cell(row, T.COL_STRENGTH, strength_text, bg)
        self._set_change_cell(row, quote, bg)
        self._update_pnl_cells(row, quote.code, quote.price)

    def _fill_stock_row(self, row: int, quote: StockQuote, color_idx: int, lite: bool = False) -> None:
        self._paint_row_cells(row, quote, color_idx)
        self._attach_qty_widget(row, quote.code)
        self._attach_trade_widgets(row, quote.code)
        self._update_est_amount_cell(row, quote.code, quote.price)
        self._code_row[quote.code] = row

    def _format_change(self, quote: StockQuote) -> tuple[str, QColor | None]:
        if quote.change_pct:
            text = T.CHANGE_AMT_FMT.format(pct=quote.change_pct, amt=quote.change_amount)
            return text, pnl_color(quote.change_pct)
        if quote.change_amount:
            return f"{quote.change_amount:+,}", pnl_color(quote.change_amount)
        return "-", None

    def _set_change_cell(self, row: int, quote: StockQuote, bg: QColor) -> None:
        text, fg = self._format_change(quote)
        self._set_cell(row, T.COL_CHANGE, text, bg, fg)

    def _update_pnl_cells(self, row: int, code: str, current: int) -> None:
        bg = QColor(row_color_for_index(row - self._stock_start_row))
        ev = self.positions.eval_pnl(code, current)
        if ev:
            amount, pct = ev
            self._set_cell(row, T.COL_PNL, f"{amount:+,}", bg, pnl_color(amount))
            self._set_cell(row, T.COL_PNL_PCT, f"{pct:+.2f}%", bg, pnl_color(pct))
        else:
            self._set_cell(row, T.COL_PNL, "-", bg)
            self._set_cell(row, T.COL_PNL_PCT, "-", bg)

        rec = self.positions.realized.get(code)
        if rec:
            self._set_cell(row, T.COL_REALIZED, f"{rec.amount:+,}", bg, pnl_color(rec.amount))
            self._set_cell(row, T.COL_REALIZED_PCT, f"{rec.pct:+.2f}%", bg, pnl_color(rec.pct))
        else:
            self._set_cell(row, T.COL_REALIZED, "-", bg)
            self._set_cell(row, T.COL_REALIZED_PCT, "-", bg)

    def _clear_stock_rows(self) -> None:
        for row in range(self._stock_start_row, self._table.rowCount()):
            for col in TRADE_WIDGET_COLS:
                self._table.removeCellWidget(row, col)
            for col in range(len(T.COL_HEADERS)):
                self._table.setItem(row, col, QTableWidgetItem(""))
        self._code_row.clear()
        self._qty_spins.clear()

    def _update_live_cells(self) -> None:
        if not self.scanner:
            return
        for code, row in list(self._code_row.items()):
            quote = self.scanner.quotes.get(code)
            if not quote:
                continue
            bg = QColor(row_color_for_index(row - self._stock_start_row))
            price_text = f"{quote.price:,}" if quote.price else "-"
            self._set_cell(row, T.COL_PRICE, price_text, bg)
            if quote.name:
                self._set_cell(row, T.COL_VENDOR, quote.name, bg)
            self._set_change_cell(row, quote, bg)
            self._update_est_amount_cell(row, code, quote.price)
            total = quote.sell_total + quote.buy_total
            sell_text = (
                T.SELL_PCT_FMT.format(pct=quote.sell_balance_pct, sell=quote.sell_total, total=total)
                if total > 0
                else "-"
            )
            strength_text = f"{quote.execution_strength:.1f}" if quote.execution_strength else "-"
            self._set_cell(row, T.COL_SELL_BAL, sell_text, bg)
            self._set_cell(row, T.COL_STRENGTH, strength_text, bg)
            self._update_pnl_cells(row, code, quote.price)

            state = quote.filter_state(
                self.config.min_sell_balance_pct,
                self.config.min_execution_strength,
            )
            status = T.NOTE_MATCH if state == "pass" else (T.NOTE_WAIT if state == "wait" else T.NOTE_FAIL)
            self._set_cell(row, T.COL_STATUS, status, bg)

    def _upgrade_pass_rows(self) -> None:
        if not self.scanner:
            return
        for code, row in list(self._code_row.items()):
            quote = self.scanner.quotes.get(code)
            if not quote:
                continue
            state = quote.filter_state(
                self.config.min_sell_balance_pct,
                self.config.min_execution_strength,
            )
            if state != "pass":
                continue
            color_idx = row - self._stock_start_row
            self._paint_row_cells(row, quote, color_idx)
            if code in self._qty_spins:
                self._update_est_amount_cell(row, code, quote.price)
                continue
            self._attach_qty_widget(row, code)
            self._attach_trade_widgets(row, code)
            self._update_est_amount_cell(row, code, quote.price)

    def refresh_grid(self, full_rebuild: bool = False) -> None:
        if self._meta_item:
            self._meta_item.setText(self._meta_text())

        if not full_rebuild and self._code_row and self.scanner:
            self._update_live_cells()
            self._upgrade_pass_rows()
            displayed = self._displayed_quotes()
            passed = self.scanner.filtered_quotes()
            self._status.showMessage(
                T.MSG_FILTER_APPLIED.format(
                    cond=self.scanner.last_condition_count,
                    count=len(displayed),
                    passed_count=len(passed),
                    sell_pct=self.config.min_sell_balance_pct,
                    strength=self.config.min_execution_strength,
                ),
                5000,
            )
            return

        self._rebuilding_grid = True
        try:
            self._clear_stock_rows()
            if not self.scanner:
                return

            if self.scanner.last_condition_count == 0:
                self._status.showMessage(T.MSG_COND_ZERO, 8000)

            displayed = self._displayed_quotes()
            lite = self.scanner.lite_rows
            if lite and len(displayed) > LITE_DISPLAY_CAP:
                displayed = displayed[:LITE_DISPLAY_CAP]
            passed = self.scanner.filtered_quotes()
            end_row = self._stock_start_row + len(displayed)
            if end_row > self._table.rowCount():
                self._table.setRowCount(end_row + 5)

            row = self._stock_start_row
            for i, quote in enumerate(displayed):
                self._fill_stock_row(row, quote, i, lite=lite)
                row += 1
                if lite and i % 200 == 0:
                    QApplication.processEvents()

            self._status.showMessage(
                T.MSG_FILTER_APPLIED.format(
                    cond=self.scanner.last_condition_count,
                    count=len(displayed),
                    passed_count=len(passed),
                    sell_pct=self.config.min_sell_balance_pct,
                    strength=self.config.min_execution_strength,
                ),
                5000,
            )
            if self.config.filter_pass_only and self.scanner.last_condition_count > len(passed):
                self._status.showMessage(
                    T.MSG_FILTER_PASS_ONLY_HINT.format(
                        total=self.scanner.last_condition_count,
                        passed=len(passed),
                    ),
                    12000,
                )
        finally:
            self._rebuilding_grid = False

    def _register_account_password(self) -> None:
        if not self.api or not self._connected:
            QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_CONN_FIRST)
            return
        QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_ACCOUNT_PW_HINT)
        self.api.show_account_password_window()

    def _prompt_account_password(self) -> None:
        if not self.api:
            return
        QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_ACCOUNT_PW_HINT)
        self.api.show_account_password_window()

    def _on_scanner_update(self) -> None:
        if self._rebuilding_grid:
            return
        self._grid_refresh_timer.start()

    def _apply_scanner_update(self) -> None:
        if not self.scanner or self._rebuilding_grid:
            return

        displayed = self._displayed_quotes()
        target_codes = self._displayed_codes()
        if not target_codes:
            return

        if not self._code_row or set(self._code_row.keys()) != target_codes:
            self.refresh_grid(full_rebuild=True)
            return

        self._update_live_cells()
        if self.scanner.lite_rows:
            self._upgrade_pass_rows()

    def _account_no(self) -> str:
        return self.config.active_account_no or self.config.account_no

    def _quote(self, code: str) -> StockQuote | None:
        return self.scanner.quotes.get(code) if self.scanner else None

    def _order_market(self, code: str, is_buy: bool) -> None:
        if not self._ensure_trade_ready():
            return
        quote = self._quote(code)
        price = quote.price if quote and quote.price else 0
        name = quote.name if quote else code
        qty = self._get_qty(code)
        ret = self.api.send_order(
            rq_name="mkt_buy" if is_buy else "mkt_sell",
            screen_no=self.config.screen_no,
            acc_no=self._account_no(),
            order_type=1 if is_buy else 2,
            code=code,
            qty=qty,
            price=0,
            hoga_gb="03",
        )
        if ret != 0:
            QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_ORDER_FAIL.format(code=ret))
            self._register_account_password()
            return
        if is_buy and price:
            self.positions.open_or_add(code, name, qty, price)
        elif not is_buy and price:
            self.positions.close(code, price)
        row = self._code_row.get(code)
        if row is not None:
            self._update_pnl_cells(row, code, price)
        self._status.showMessage(T.MSG_ORDER_SENT.format(name=name), 3000)

    def _order_limit(self, code: str, is_buy: bool, edit: QLineEdit) -> None:
        if not self._ensure_trade_ready():
            return
        raw = edit.text().replace(",", "").strip()
        if not raw.isdigit():
            QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_BAD_PRICE)
            return
        limit_price = int(raw)
        quote = self._quote(code)
        name = quote.name if quote else code
        qty = self._get_qty(code)
        ret = self.api.send_order(
            rq_name="lmt_buy" if is_buy else "lmt_sell",
            screen_no=self.config.screen_no,
            acc_no=self._account_no(),
            order_type=1 if is_buy else 2,
            code=code,
            qty=qty,
            price=limit_price,
            hoga_gb="00",
        )
        if ret != 0:
            QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_ORDER_FAIL.format(code=ret))
            self._register_account_password()
            return
        if is_buy:
            self.positions.open_or_add(code, name, qty, limit_price)
        else:
            self.positions.close(code, limit_price)
        live = quote.price if quote and quote.price else limit_price
        row = self._code_row.get(code)
        if row is not None:
            self._update_pnl_cells(row, code, live)
        self._status.showMessage(T.MSG_ORDER_SENT.format(name=name), 3000)

    def _ensure_trade_ready(self) -> bool:
        if not self.api or not self._connected or not self._account_no():
            QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_NEED_CONNECT)
            return False
        return True

    def _on_chejan(self, gubun: str, item_cnt: int, fid_list: str) -> None:
        if gubun != "0" or not self.api:
            return
        if self.api.get_chejan_data(913) != T.FILL_DONE:
            return
        code = self.api.get_chejan_data(9001).replace("A", "")
        price = int(self.api.get_chejan_data(910) or "0")
        qty = int(self.api.get_chejan_data(911) or "0")
        order_type = self.api.get_chejan_data(905)
        name = self.api.get_chejan_data(302)
        if "\ub9e4\uc218" in order_type:
            self.positions.open_or_add(code, name, qty, price)
        elif "\ub9e4\ub3c4" in order_type:
            self.positions.close(code, price)
        row = self._code_row.get(code)
        quote = self._quote(code)
        if row is not None and quote:
            self._update_pnl_cells(row, code, quote.price)

    def _prompt_connect(self) -> None:
        if self._connected:
            return
        self._status.showMessage(T.STATUS_PRESS_F5, 0)
        hint = T.MSG_PRESS_F5_REMOTE if self._remote_mode else T.MSG_PRESS_F5
        QMessageBox.information(self, T.MSG_ERP_TITLE, hint)

    def _run_bg(self, label: str, work, *, cancellable: bool = True) -> bool:
        progress = QProgressDialog(label, T.BTN_CANCEL if cancellable else "", 0, 0, self)
        progress.setWindowTitle(T.MSG_ERP_TITLE)
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)
        if not cancellable:
            progress.setCancelButton(None)
        progress.show()
        state = {"done": False, "ok": False, "err": None, "text": label}

        def runner() -> None:
            try:
                state["ok"] = bool(work(lambda msg: state.update(text=msg)))
            except Exception as exc:
                state["err"] = exc
                state["ok"] = False
            finally:
                state["done"] = True

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        while not state["done"]:
            progress.setLabelText(state["text"])
            QApplication.processEvents()
            if cancellable and progress.wasCanceled():
                return False
            thread.join(0.05)
        progress.close()
        if state["err"] is not None:
            QMessageBox.warning(self, T.MSG_ERP_TITLE, str(state["err"]))
        return state["ok"]

    def _tick_status(self) -> None:
        sync = T.STATUS_LINKED if self._connected else T.STATUS_WAIT
        self._status.showMessage(T.STATUS_FMT.format(t=datetime.now().strftime("%H:%M"), sync=sync))

    def _start_sync(self) -> None:
        if self.scanner and self._connected:
            if self._selected_conditions:
                if self._bridge:
                    added = self._bridge.refresh_snapshot()
                else:
                    added = self.scanner.refresh_condition_snapshot()
                if added:
                    self._status.showMessage(
                        T.MSG_COND_REFRESH.format(
                            added=added,
                            total=self.scanner.last_condition_count,
                        ),
                        5000,
                    )
            self.refresh_grid(full_rebuild=True)
            self._status.showMessage(T.MSG_REFRESH_OK, 3000)
            return
        self._connect_and_run()

    def _save_condition_choice(self, selected: list[ConditionChoice]) -> None:
        self._selected_conditions = selected
        if selected:
            self.config.condition_name = selected[0].name
            self.config.condition_index = selected[0].index
        else:
            self.config.condition_name = ""
            self.config.condition_index = 0
        save_config(self.config)

    def _pick_conditions(self) -> None:
        if not self.api or not self._connected:
            QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_CONN_FIRST)
            return
        selected = pick_conditions(self.api, self)
        if selected is None:
            return
        self._save_condition_choice(selected)
        if self.scanner:
            self._code_row.clear()
            self._qty_spins.clear()
            if self._bridge:
                self._bridge.bootstrap(selected, self.config)
                self.scanner = self._bridge.scanner
                if self.scanner:
                    self.scanner.on_state_change = self._on_scanner_update
            else:
                self.scanner.bootstrap(conditions=selected)
            self.refresh_grid(full_rebuild=True)
            self._show_bootstrap_status(selected)

    def _show_bootstrap_status(self, selected: list[ConditionChoice]) -> None:
        if not self.scanner:
            return
        count = self.scanner.last_condition_count
        if selected:
            names = ", ".join(c.name for c in selected)
            self._status.showMessage(T.MSG_COND_APPLIED.format(names=names), 5000)
            if count:
                self._status.showMessage(T.MSG_COND_COUNT.format(count=count), 8000)
        elif self.scanner.market_mode and count:
            self._status.showMessage(T.MSG_MARKET_COUNT.format(count=count), 8000)
        elif count:
            self._status.showMessage(T.MSG_WATCH_COUNT.format(count=count), 8000)
        else:
            self._status.showMessage(T.MSG_COND_ZERO, 8000)

    def _edit_filters(self) -> None:
        if edit_filters(self.config, parent=self):
            self._sell_spin.setValue(self.config.min_sell_balance_pct)
            self._strength_spin.setValue(self.config.min_execution_strength)
            self._pass_only_chk.setChecked(self.config.filter_pass_only)
            save_config(self.config)
            self._code_row.clear()
            self._qty_spins.clear()
            self.refresh_grid(full_rebuild=True)

    def _connect_and_run(self) -> None:
        if self._remote_mode:
            self._connect_remote()
            return
        if self.config.use_mock:
            QMessageBox.information(self, T.MSG_ERP_TITLE, T.MSG_ERP_BODY)

        if self.api is None:
            try:
                self.api = KiwoomAPI()
            except RuntimeError as exc:
                QMessageBox.critical(self, T.MSG_ERP_TITLE, str(exc))
                return

        err = self.api.comm_connect()
        if err != 0 or not self.api.is_connected():
            detail = KiwoomAPI.login_error_text(err)
            QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_CONN_FAIL_FMT.format(detail=detail))
            return

        server = self.api.get_login_info("GetServerGubun")
        accounts = self.api.get_accounts()
        if self.config.use_mock and server != "1":
            QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_NOT_MOCK)
            return

        if accounts:
            acc = accounts[0]
            if self.config.use_mock:
                self.config.mock_account_no = acc
            self.config.account_no = acc
            save_config(self.config)

        self._prompt_account_password()

        selected = pick_conditions(self.api, self)
        if selected is None:
            selected = []
        self._save_condition_choice(selected)

        self.api.register_chejan_callback(self._on_chejan)
        self.scanner = ConditionStockScanner(
            api=self.api,
            config=self.config,
            on_state_change=self._on_scanner_update,
        )
        self.scanner.bootstrap(conditions=selected)
        self._connected = True
        self.refresh_grid(full_rebuild=True)
        self._show_bootstrap_status(selected)
        self._status.showMessage(T.MSG_LINK_OK, 5000)

    def _connect_remote(self) -> None:
        from auto_trader.remote_client import RemoteBridgeClient

        if self._bridge is None:
            host = self.config.bridge_host.strip()
            if not host:
                QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_BRIDGE_HOST_EMPTY)
                return
            self._bridge = RemoteBridgeClient(
                host=host,
                port=int(self.config.bridge_port or 8765),
                token=self.config.bridge_token,
                http_port=int(self.config.bridge_http_port or 8766),
            )

        bridge = self._bridge

        def connect_work(on_tick) -> bool:
            return bridge.connect(timeout_sec=30.0, on_tick=on_tick)

        if not self._run_bg(T.PROGRESS_BRIDGE_CONNECT, connect_work):
            QMessageBox.warning(self, T.MSG_ERP_TITLE, T.MSG_BRIDGE_CONN_FAIL)
            return

        self.api = bridge.create_api()
        accounts = self.api.get_accounts()
        if accounts:
            acc = accounts[0]
            self.config.account_no = acc
            if self.config.use_mock:
                self.config.mock_account_no = acc
            save_config(self.config)

        selected = pick_conditions(self.api, self)
        if selected is None:
            selected = []
        self._save_condition_choice(selected)

        self.api.register_chejan_callback(self._on_chejan)
        self.scanner = bridge.attach_scanner(self.config)
        self.scanner.on_state_change = self._on_scanner_update

        def bootstrap_work(on_tick) -> bool:
            on_tick(T.PROGRESS_LOAD_DATA)
            bridge.bootstrap(selected, self.config)
            return True

        if not self._run_bg(T.PROGRESS_LOAD_DATA, bootstrap_work, cancellable=False):
            return

        self._connected = True
        self.refresh_grid(full_rebuild=True)
        self._show_bootstrap_status(selected)
        self._status.showMessage(T.MSG_BRIDGE_LINK_OK, 5000)


def run_excel_ui(config: TraderConfig | None = None, remote: bool = False) -> int:
    cfg = config or load_config()
    bridge = None
    if remote or cfg.bridge_role == "client":
        from auto_trader.remote_client import RemoteBridgeClient

        host = cfg.bridge_host.strip()
        if host:
            bridge = RemoteBridgeClient(
                host=host,
                port=int(cfg.bridge_port or 8765),
                token=cfg.bridge_token,
                http_port=int(cfg.bridge_http_port or 8766),
            )
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    win = ExcelDisguiseWindow(config=cfg, bridge=bridge)
    win.show()
    return app.exec_()
