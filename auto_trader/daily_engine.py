"""당일매매 엔진: 조건식 통과 + 매도잔량/체결강도 + 고점 추적 매도."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from auto_trader.brm_engine import BrmPaperBook
from auto_trader.daily_params import DailyParams
from auto_trader.indicators import rsi
from auto_trader.minute_bars import MinuteBarStore

logger = logging.getLogger(__name__)


class DailyAction(str, Enum):
    NONE = "NONE"
    BUY = "BUY"
    SELL_TRAIL = "SELL_TRAIL"
    SELL_TP = "SELL_TP"
    SELL_STOP = "SELL_STOP"
    SELL_WEAK = "SELL_WEAK"
    SELL_RSI = "SELL_RSI"
    SELL_FLAT = "SELL_FLAT"


@dataclass
class DailySignal:
    code: str
    name: str
    action: DailyAction
    price: float
    qty: int
    reason: str
    sell_pct: float = 0.0
    strength: float = 0.0
    peak: float = 0.0


@dataclass
class _LivePos:
    qty: int
    avg_price: float
    peak: float
    entries: int = 1


@dataclass
class DailyEngine:
    params: DailyParams
    book: BrmPaperBook = field(default_factory=BrmPaperBook)
    _peaks: dict[str, float] = field(default_factory=dict)
    _log_path: Path | None = None

    def _in_session(self, now: datetime) -> bool:
        t = now.time()
        return self.params.t_session_start <= t < self.params.t_session_end

    def _must_flat(self, now: datetime) -> bool:
        return now.time() >= self.params.t_force_flat

    def _entry_ok(self, sell_pct: float, strength: float, sell_total: int, buy_total: int) -> bool:
        p = self.params
        if sell_total > 0 and buy_total > 0 and sell_total <= buy_total:
            return False
        if sell_pct > 0 and sell_pct < p.min_sell_balance_pct:
            return False
        if p.min_execution_strength > 0 and strength > 0 and strength < p.min_execution_strength:
            return False
        return True

    def _rsi_last(self, store: MinuteBarStore | None) -> float | None:
        if store is None or len(store.bars) < self.params.rsi_period + 2:
            return None
        r = rsi(store.closes(), self.params.rsi_period)
        v = r[-1]
        return v

    def evaluate(
        self,
        code: str,
        name: str,
        price: float,
        sell_pct: float,
        strength: float,
        sell_total: int,
        buy_total: int,
        now: datetime,
        store: MinuteBarStore | None = None,
    ) -> DailySignal:
        base = DailySignal(code, name, DailyAction.NONE, price, 0, "")
        p = self.params
        if price <= 0:
            return base

        pos = self.book.positions.get(code)
        if pos:
            peak = self._peaks.get(code, float(pos.avg_price))
            if price > peak:
                peak = float(price)
                self._peaks[code] = peak

            if self._must_flat(now):
                return DailySignal(code, name, DailyAction.SELL_FLAT, price, pos.qty, "15:20 flat", sell_pct, strength, peak)

            pnl_pct = (price - pos.avg_price) / pos.avg_price * 100.0
            if pnl_pct <= -p.stop_loss_pct:
                return DailySignal(code, name, DailyAction.SELL_STOP, price, pos.qty, f"stop -{p.stop_loss_pct}%", sell_pct, strength, peak)

            if pnl_pct >= p.take_profit_pct:
                return DailySignal(code, name, DailyAction.SELL_TP, price, pos.qty, f"tp +{p.take_profit_pct}%", sell_pct, strength, peak)

            if pnl_pct >= p.min_profit_to_trail_pct and peak > 0:
                drop = (peak - price) / peak * 100.0
                if drop >= p.trail_from_peak_pct:
                    return DailySignal(
                        code, name, DailyAction.SELL_TRAIL, price, pos.qty,
                        f"peak trail -{p.trail_from_peak_pct}%", sell_pct, strength, peak,
                    )

            rsi_v = self._rsi_last(store)
            if p.use_rsi_peak_exit and rsi_v is not None and rsi_v >= p.rsi_exit_high and pnl_pct > 0:
                return DailySignal(code, name, DailyAction.SELL_RSI, price, pos.qty, f"RSI {rsi_v:.0f}", sell_pct, strength, peak)

            if strength > 0 and strength < p.exit_strength_below and sell_pct < p.exit_sell_balance_below:
                return DailySignal(code, name, DailyAction.SELL_WEAK, price, pos.qty, "hoga weak", sell_pct, strength, peak)

            return base

        if not self._in_session(now) or now.time() >= p.t_entry_cutoff:
            return base
        if len(self.book.positions) >= p.max_positions:
            return base
        if not self._entry_ok(sell_pct, strength, sell_total, buy_total):
            return base

        return DailySignal(
            code, name, DailyAction.BUY, price, max(1, p.base_qty),
            "cond+hoga", sell_pct, strength, price,
        )

    def apply_signal(self, sig: DailySignal, now: datetime) -> None:
        if sig.action == DailyAction.NONE:
            return
        if sig.action == DailyAction.BUY:
            self.book.open_or_add(sig.code, sig.name, sig.qty, sig.price, now, is_add=False)
            self._peaks[sig.code] = sig.price
        else:
            self.book.close(sig.code, sig.price, sig.action.value)
            self._peaks.pop(sig.code, None)
        self._log(sig, now)

    def _log(self, sig: DailySignal, now: datetime) -> None:
        if not self.params.log_signals:
            return
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        if self._log_path is None or self._log_path.name != f"daily_{now:%Y%m%d}.csv":
            self._log_path = log_dir / f"daily_{now:%Y%m%d}.csv"
            if not self._log_path.exists():
                with self._log_path.open("w", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerow(
                        ["time", "code", "name", "action", "price", "qty", "reason", "sell_pct", "strength", "peak"]
                    )
        with self._log_path.open("a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(
                [
                    now.strftime("%H:%M:%S"), sig.code, sig.name, sig.action.value,
                    f"{sig.price:.0f}", sig.qty, sig.reason,
                    f"{sig.sell_pct:.1f}", f"{sig.strength:.1f}", f"{sig.peak:.0f}",
                ]
            )
        logger.info("DAILY %s %s %s @%s %s", sig.action.value, sig.code, sig.name, sig.price, sig.reason)
