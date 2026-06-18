"""Condition stock scanner with sell-balance and execution-strength filters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Literal

from PyQt5.QtCore import QTimer

from auto_trader import i18n_ko as T
from auto_trader.condition_picker import ConditionChoice
from auto_trader.config import TraderConfig
from auto_trader.kiwoom_api import KiwoomAPI, normalize_stock_code

logger = logging.getLogger(__name__)

FID_PRICE = 10
FID_CHANGE = 11
FID_CHANGE_RATE = 12
FID_SELL_TOTAL = 121
FID_BUY_TOTAL = 125
FID_EXEC_STRENGTH = 228
REAL_FIDS = "10;11;12;121;125;228"
LITE_ROW_THRESHOLD = 80
NAME_BATCH_SIZE = 40
FilterState = Literal["wait", "pass", "fail"]


@dataclass
class StockQuote:
    code: str
    name: str = ""
    price: int = 0
    change_amount: int = 0
    change_pct: float = 0.0
    sell_total: int = 0
    buy_total: int = 0
    execution_strength: float = 0.0

    @property
    def sell_balance_pct(self) -> float:
        total = self.sell_total + self.buy_total
        if total <= 0:
            return 0.0
        return self.sell_total / total * 100.0

    def filter_state(self, min_sell_pct: float, min_strength: float) -> FilterState:
        if self.price <= 0:
            return "wait"
        has_hoga = self.sell_total + self.buy_total > 0
        has_strength = self.execution_strength > 0
        if not has_hoga and not has_strength:
            return "wait"
        if has_hoga and self.sell_balance_pct < min_sell_pct:
            return "fail"
        if min_strength > 0:
            if has_strength and self.execution_strength < min_strength:
                return "fail"
            if not has_strength:
                return "wait"
        return "pass"

    def passes_filter(self, min_sell_pct: float, min_strength: float) -> bool:
        return self.filter_state(min_sell_pct, min_strength) == "pass"


@dataclass
class ConditionStockScanner:
    api: KiwoomAPI
    config: TraderConfig
    quotes: dict[str, StockQuote] = field(default_factory=dict)
    condition_codes: list[str] = field(default_factory=list)
    last_condition_count: int = 0
    market_mode: bool = False
    lite_rows: bool = False
    on_state_change: Callable[[], None] | None = None
    _active_conditions: list[tuple[str, ConditionChoice]] = field(default_factory=list)
    _realtime_registered: bool = False
    _tr_queue: list[str] = field(default_factory=list)
    _name_queue: list[str] = field(default_factory=list)

    def _notify(self) -> None:
        if self.on_state_change:
            self.on_state_change()

    def _stop_conditions(self) -> None:
        for screen, cond in self._active_conditions:
            try:
                self.api.send_condition_stop(screen, cond.name, cond.index)
            except Exception:
                pass
        self._active_conditions.clear()

    def bootstrap(self, conditions: list[ConditionChoice] | None = None) -> None:
        self._stop_conditions()
        self.quotes.clear()
        self.condition_codes.clear()
        self._tr_queue.clear()
        self._name_queue.clear()
        self._realtime_registered = False
        self.market_mode = False
        self.lite_rows = False

        # conditions=[] means user explicitly skipped the picker.
        explicit = conditions is not None
        runtime: list[ConditionChoice] = []
        if explicit:
            runtime = list(conditions)
        elif self.config.condition_name:
            runtime = [
                ConditionChoice(index=self.config.condition_index, name=self.config.condition_name)
            ]

        codes: list[str] = []
        base_screen = int(self.config.condition_screen_no)

        if runtime:
            for i, cond in enumerate(runtime):
                screen = f"{base_screen + i:04d}"
                loaded = self._load_condition_codes(cond.index, cond.name, screen)
                logger.info("condition [%s] screen=%s -> %d codes", cond.name, screen, len(loaded))
                codes.extend(loaded)
                self._active_conditions.append((screen, cond))
            self.api.register_real_condition_callback(self.on_real_condition)
        elif self.config.watch_mode == "market":
            codes = self.api.get_all_stock_codes()
            self.market_mode = True
            self.lite_rows = len(codes) > LITE_ROW_THRESHOLD
            logger.info("market mode -> %d codes (lite=%s)", len(codes), self.lite_rows)
        else:
            codes = list(self.config.watch_codes)
            logger.info("watch_codes mode -> %s", codes)

        self.condition_codes = list(dict.fromkeys(normalize_stock_code(c) for c in codes if c))
        self.last_condition_count = len(self.condition_codes)

        if self.market_mode:
            for code in self.condition_codes:
                self.quotes[code] = StockQuote(code=code)
            self._notify()
            if not self.condition_codes:
                return
            self._start_name_queue(list(self.condition_codes))
            self._register_realtime(self.condition_codes, replace=True)
            self.api.register_real_callback(self.on_real_data)
            return

        for code in self.condition_codes:
            self._ensure_stock(code, fetch_tr=False)
        self.lite_rows = len(self.condition_codes) > LITE_ROW_THRESHOLD

        self._notify()

        if not self.condition_codes:
            return

        self._register_realtime(self.condition_codes, replace=True)
        self.api.register_real_callback(self.on_real_data)
        self._notify()
        self._start_tr_queue(list(self.condition_codes))

    def refresh_condition_snapshot(self) -> int:
        """Re-run condition snapshot search to pick up newly matched stocks."""
        if not self._active_conditions:
            return 0
        before = len(self.quotes)
        new_codes: list[str] = []
        for screen, cond in self._active_conditions:
            self.api.send_condition(screen, cond.name, cond.index, 0)
            for code in self.api.condition_codes:
                nc = normalize_stock_code(code)
                if not nc:
                    continue
                if nc not in self.quotes:
                    new_codes.append(nc)
                self._ensure_stock(nc, fetch_tr=False)
        if new_codes:
            self._register_realtime(new_codes, replace=False)
            self._start_tr_queue(new_codes)
        self.last_condition_count = len(self.condition_codes)
        self.lite_rows = len(self.condition_codes) > LITE_ROW_THRESHOLD
        self._notify()
        return len(self.quotes) - before

    def _start_name_queue(self, codes: list[str]) -> None:
        self._name_queue = list(codes)
        QTimer.singleShot(0, self._process_name_queue_step)

    def _process_name_queue_step(self) -> None:
        if not self._name_queue:
            self._notify()
            return
        for _ in range(NAME_BATCH_SIZE):
            if not self._name_queue:
                break
            code = self._name_queue.pop(0)
            q = self.quotes.get(code)
            if q is None:
                continue
            if not q.name:
                q.name = self.api.get_master_code_name(code)
            if q.price <= 0:
                self._ensure_master_price(code)
        self._notify()
        QTimer.singleShot(5, self._process_name_queue_step)

    def _start_tr_queue(self, codes: list[str]) -> None:
        self._tr_queue = list(codes)
        QTimer.singleShot(0, self._process_tr_queue_step)

    def _process_tr_queue_step(self) -> None:
        if not self._tr_queue:
            self._notify()
            return
        code = self._tr_queue.pop(0)
        self._fetch_snapshot(code)
        self._fetch_hoga_snapshot(code)
        self._notify()
        QTimer.singleShot(250, self._process_tr_queue_step)

    def _load_condition_codes(self, cond_index: int, cond_name: str, screen_no: str) -> list[str]:
        merged: list[str] = []

        def absorb() -> None:
            for code in self.api.condition_codes:
                nc = normalize_stock_code(code)
                if nc and nc not in merged:
                    merged.append(nc)

        ret0 = self.api.send_condition(screen_no, cond_name, cond_index, 0)
        absorb()
        if ret0 != 1:
            logger.warning("SendCondition snapshot failed ret=%s name=%s", ret0, cond_name)

        ret1 = self.api.send_condition(screen_no, cond_name, cond_index, 1)
        absorb()
        if ret1 != 1:
            logger.warning("SendCondition realtime failed ret=%s name=%s", ret1, cond_name)

        logger.info(
            "condition [%s] merged=%d sample=%s",
            cond_name,
            len(merged),
            merged[:12],
        )
        return merged

    @staticmethod
    def _parse_price(raw: str) -> int:
        text = raw.strip().replace(",", "").lstrip("+-")
        if not text:
            return 0
        try:
            return abs(int(text))
        except ValueError:
            return 0

    @staticmethod
    def _parse_signed_int(raw: str) -> int:
        text = raw.strip().replace(",", "")
        if not text:
            return 0
        try:
            return int(text)
        except ValueError:
            return 0

    @staticmethod
    def _parse_float(raw: str) -> float:
        text = raw.strip().replace(",", "").lstrip("+-")
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _ensure_master_price(self, code: str) -> None:
        q = self.quotes.get(code)
        if q is None or q.price > 0:
            return
        price = self.api.get_master_last_price(code)
        if price:
            q.price = price

    def _ensure_stock(self, code: str, fetch_tr: bool = True) -> StockQuote:
        code = normalize_stock_code(code)
        q = self.quotes.get(code)
        if q is None:
            q = StockQuote(code=code, name=self.api.get_master_code_name(code))
            self.quotes[code] = q
            if code not in self.condition_codes:
                self.condition_codes.append(code)
                self.last_condition_count = len(self.condition_codes)
        if not q.name:
            q.name = self.api.get_master_code_name(code)
        self._ensure_master_price(code)
        if fetch_tr:
            self._fetch_snapshot(code)
            self._fetch_hoga_snapshot(code)
        return q

    def _fetch_snapshot(self, code: str) -> None:
        q = self._ensure_stock(code, fetch_tr=False)

        self.api.set_input_value(T.F_STOCK_CODE, code)
        rq = f"price_{code}"
        screen = self.config.tr_screen_no
        if self.api.comm_rq_data(rq, "opt10001", 0, screen) == 0:
            name = self.api.get_comm_data("opt10001", rq, 0, T.F_STOCK_NAME).strip()
            if name:
                q.name = name
            for field in (T.F_CURRENT_PRICE, T.F_REF_PRICE):
                price = self._parse_price(self.api.get_comm_data("opt10001", rq, 0, field))
                if price:
                    q.price = price
                    break
            chg = self._parse_signed_int(self.api.get_comm_data("opt10001", rq, 0, T.F_CHANGE))
            if chg:
                q.change_amount = chg
            rate_raw = self.api.get_comm_data("opt10001", rq, 0, T.F_CHANGE_RATE)
            rate = self._parse_float(rate_raw)
            if rate:
                q.change_pct = -abs(rate) if str(rate_raw).strip().startswith("-") else abs(rate)

        if q.price <= 0:
            self._ensure_master_price(code)

    def _fetch_hoga_snapshot(self, code: str) -> None:
        self.api.set_input_value(T.F_STOCK_CODE, code)
        rq = f"hoga_{code}"
        if self.api.comm_rq_data(rq, "opt10004", 0, self.config.tr_screen_no) != 0:
            return
        q = self.quotes.setdefault(code, StockQuote(code=code))
        sell = self._parse_price(self.api.get_comm_data("opt10004", rq, 0, T.F_SELL_TOTAL))
        buy = self._parse_price(self.api.get_comm_data("opt10004", rq, 0, T.F_BUY_TOTAL))
        if sell:
            q.sell_total = sell
        if buy:
            q.buy_total = buy

    def _register_realtime(self, codes: list[str], replace: bool = False) -> None:
        if not codes:
            return
        opt = "0" if replace or not self._realtime_registered else "1"
        joined = ";".join(codes)
        if len(codes) <= 100:
            self.api.set_real_reg(self.config.real_screen_no, joined, REAL_FIDS, opt)
            self._realtime_registered = True
            return
        for i in range(0, len(codes), 100):
            chunk = ";".join(codes[i : i + 100])
            chunk_opt = "0" if (replace and i == 0) else "1"
            screen = (
                self.config.real_screen_no
                if i == 0
                else f"{int(self.config.real_screen_no) + i // 100:04d}"
            )
            self.api.set_real_reg(screen, chunk, REAL_FIDS, chunk_opt)
        self._realtime_registered = True

    def on_real_condition(self, code: str, event_type: str, cond_name: str, cond_index: str) -> None:
        code = normalize_stock_code(code)
        if event_type == "D":
            return
        if event_type != "I":
            return
        was_new = code not in self.quotes
        logger.info("real condition insert: %s (%s) new=%s", code, cond_name, was_new)
        self._ensure_stock(code, fetch_tr=False)
        if was_new:
            self._register_realtime([code], replace=False)
            QTimer.singleShot(50, lambda c=code: self._deferred_fetch(c))
        self.lite_rows = len(self.condition_codes) > LITE_ROW_THRESHOLD
        self._notify()

    def _deferred_fetch(self, code: str) -> None:
        self._fetch_snapshot(code)
        self._fetch_hoga_snapshot(code)
        self._notify()

    def on_real_data(self, code: str, real_type: str, real_data: str) -> None:
        code = normalize_stock_code(code)
        q = self.quotes.get(code)
        if q is None:
            return

        price = self._parse_price(self.api.get_comm_real_data(code, FID_PRICE))
        if price:
            q.price = price
        chg = self._parse_signed_int(self.api.get_comm_real_data(code, FID_CHANGE))
        if chg:
            q.change_amount = chg
        rate_raw = self.api.get_comm_real_data(code, FID_CHANGE_RATE)
        rate = self._parse_float(rate_raw)
        if rate:
            q.change_pct = -abs(rate) if str(rate_raw).strip().startswith("-") else abs(rate)

        if real_type == T.REAL_TICK or "\uccb4\uacb0" in real_type:
            strength = self.api.get_comm_real_data(code, FID_EXEC_STRENGTH)
            if strength:
                try:
                    q.execution_strength = float(strength)
                except ValueError:
                    pass
        if real_type == T.REAL_HOGA or "\ud638\uac00" in real_type:
            sell = self._parse_price(self.api.get_comm_real_data(code, FID_SELL_TOTAL))
            buy = self._parse_price(self.api.get_comm_real_data(code, FID_BUY_TOTAL))
            if sell:
                q.sell_total = sell
            if buy:
                q.buy_total = buy

        self._notify()

    def filtered_quotes(self) -> list[StockQuote]:
        min_sell = self.config.min_sell_balance_pct
        min_strength = self.config.min_execution_strength
        rows = [q for q in self.quotes.values() if q.passes_filter(min_sell, min_strength)]
        rows.sort(key=lambda q: (-q.sell_balance_pct, -q.execution_strength, q.name))
        return rows

    def display_quotes(self) -> list[StockQuote]:
        min_sell = self.config.min_sell_balance_pct
        min_strength = self.config.min_execution_strength
        if self.config.filter_pass_only:
            return self.filtered_quotes()

        rows = list(self.quotes.values())
        rows.sort(
            key=lambda q: (
                0 if q.filter_state(min_sell, min_strength) == "pass" else 1,
                0 if q.filter_state(min_sell, min_strength) == "wait" else 1,
                -q.sell_balance_pct,
                q.name,
            )
        )
        return rows
