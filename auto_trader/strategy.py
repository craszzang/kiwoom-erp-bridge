"""Example momentum strategy."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from auto_trader import i18n_ko as T
from auto_trader.condition_picker import ConditionChoice
from auto_trader.config import TraderConfig
from auto_trader.kiwoom_api import KiwoomAPI

logger = logging.getLogger(__name__)


@dataclass
class Position:
    code: str
    name: str
    qty: int
    entry_price: int


@dataclass
class SimpleMomentumStrategy:
    api: KiwoomAPI
    config: TraderConfig
    positions: dict[str, Position] = field(default_factory=dict)
    ref_prices: dict[str, int] = field(default_factory=dict)
    live_prices: dict[str, int] = field(default_factory=dict)
    stock_names: dict[str, str] = field(default_factory=dict)
    on_state_change: Callable[[], None] | None = None

    @property
    def account_no(self) -> str:
        return self.config.active_account_no or self.config.account_no

    def _notify(self) -> None:
        if self.on_state_change:
            self.on_state_change()

    def bootstrap(self, conditions: list[ConditionChoice] | None = None) -> None:
        codes = list(self.config.watch_codes)
        runtime = list(conditions or [])
        if not runtime and self.config.condition_name:
            runtime = [
                ConditionChoice(index=self.config.condition_index, name=self.config.condition_name)
            ]

        for cond in runtime:
            codes.extend(self._load_condition_codes(cond.index, cond.name))
        codes = list(dict.fromkeys(codes))
        if not codes:
            return
        for code in codes:
            self._fetch_reference_price(code)
        fids = "10;12;20"
        self.api.set_real_reg(self.config.real_screen_no, ";".join(codes), fids, "0")
        self.api.register_real_callback(self.on_real_data)
        self.api.register_chejan_callback(self.on_chejan)
        self._notify()

    def _load_condition_codes(self, cond_index: int, cond_name: str) -> list[str]:
        self.api.send_condition(
            self.config.screen_no,
            cond_name,
            cond_index,
            0,
        )
        return self.api.condition_codes

    def _fetch_reference_price(self, code: str) -> None:
        self.api.set_input_value(T.F_STOCK_CODE, code)
        ret = self.api.comm_rq_data(T.RQ_REF, "opt10001", 0, self.config.screen_no)
        if ret != 0:
            return
        price = int(self.api.get_comm_data("opt10001", T.RQ_REF, 0, T.F_REF_PRICE) or "0")
        name = self.api.get_comm_data("opt10001", T.RQ_REF, 0, T.F_STOCK_NAME)
        if price > 0:
            self.ref_prices[code] = price
            self.live_prices[code] = price
        if name:
            self.stock_names[code] = name.strip()

    def on_real_data(self, code: str, real_type: str, real_data: str) -> None:
        if real_type != T.REAL_TICK:
            return
        current = int(self.api.get_comm_real_data(code, 10) or "0")
        if current <= 0:
            return
        self.live_prices[code] = current
        ref = self.ref_prices.get(code)
        if not ref:
            self._notify()
            return
        change_pct = (current - ref) / ref * 100
        if code not in self.positions and len(self.positions) < self.config.max_positions:
            if change_pct <= -self.config.buy_drop_pct:
                self._buy(code)
        elif code in self.positions:
            pos = self.positions[code]
            pnl = (current - pos.entry_price) / pos.entry_price * 100
            if pnl >= self.config.sell_rise_pct:
                self._sell(code, pos.qty)
        self._notify()

    def on_chejan(self, gubun: str, item_cnt: int, fid_list: str) -> None:
        if gubun != "0":
            return
        code = self.api.get_chejan_data(9001).replace("A", "")
        if self.api.get_chejan_data(913) != T.FILL_DONE:
            return
        price = int(self.api.get_chejan_data(910) or "0")
        qty = int(self.api.get_chejan_data(911) or "0")
        order_type = self.api.get_chejan_data(905)
        name = self.api.get_chejan_data(302)
        if "\ub9e4\uc218" in order_type:
            self.positions[code] = Position(code=code, name=name, qty=qty, entry_price=price)
            self.stock_names[code] = name
        elif "\ub9e4\ub3c4" in order_type and code in self.positions:
            del self.positions[code]
        self._notify()

    def _buy(self, code: str) -> None:
        if not self.account_no:
            return
        self.api.send_order(
            rq_name="buy",
            screen_no=self.config.screen_no,
            acc_no=self.account_no,
            order_type=1,
            code=code,
            qty=self.config.order_qty,
            price=0,
            hoga_gb="03",
        )

    def _sell(self, code: str, qty: int) -> None:
        self.api.send_order(
            rq_name="sell",
            screen_no=self.config.screen_no,
            acc_no=self.account_no,
            order_type=2,
            code=code,
            qty=qty,
            price=0,
            hoga_gb="03",
        )
