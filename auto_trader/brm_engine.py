"""BRM v3 paper engine: entries, scale-in, exits, 09-11 session, stop-loss."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from auto_trader.brm_params import BrmParams
from auto_trader.indicators import bollinger, crossed_under, lowest, macd, rsi
from auto_trader.minute_bars import MinuteBarStore

logger = logging.getLogger(__name__)


class BrmAction(str, Enum):
    NONE = "NONE"
    ENTRY = "ENTRY"
    ADD = "ADD"
    TP = "TP"
    STOP = "STOP"
    TIME_FLAT = "TIME_FLAT"
    B_EXIT = "B_EXIT"
    R_EXIT = "R_EXIT"
    M_EXIT = "M_EXIT"


@dataclass
class BrmPaperPosition:
    code: str
    name: str
    qty: int
    avg_price: float
    entries: int = 1
    opened_at: datetime | None = None


@dataclass
class BrmSignal:
    code: str
    name: str
    action: BrmAction
    price: float
    qty: int
    reason: str
    rsi: float | None = None
    sell_pct: float | None = None
    strength: float | None = None
    session_vol: int = 0


@dataclass
class BrmSessionStats:
    entries: int = 0
    adds: int = 0
    exits: int = 0
    wins: int = 0
    losses: int = 0
    realized_pnl: float = 0.0


@dataclass
class BrmPaperBook:
    positions: dict[str, BrmPaperPosition] = field(default_factory=dict)
    stats: BrmSessionStats = field(default_factory=BrmSessionStats)
    closed_trades: list[dict] = field(default_factory=list)

    def open_or_add(
        self,
        code: str,
        name: str,
        qty: int,
        price: float,
        now: datetime,
        *,
        is_add: bool,
    ) -> None:
        pos = self.positions.get(code)
        if pos is None:
            self.positions[code] = BrmPaperPosition(
                code=code, name=name, qty=qty, avg_price=price, opened_at=now
            )
            self.stats.entries += 1
            return
        total = pos.qty + qty
        pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total
        pos.qty = total
        if is_add:
            pos.entries += 1
            self.stats.adds += 1

    def close(self, code: str, price: float, reason: str) -> float | None:
        pos = self.positions.pop(code, None)
        if pos is None or pos.avg_price <= 0:
            return None
        pnl_pct = (price - pos.avg_price) / pos.avg_price * 100.0
        pnl_amt = (price - pos.avg_price) * pos.qty
        self.stats.exits += 1
        self.stats.realized_pnl += pnl_amt
        if pnl_amt >= 0:
            self.stats.wins += 1
        else:
            self.stats.losses += 1
        self.closed_trades.append(
            {
                "code": code,
                "name": pos.name,
                "reason": reason,
                "avg": pos.avg_price,
                "exit": price,
                "qty": pos.qty,
                "pnl_pct": pnl_pct,
                "pnl_amt": pnl_amt,
            }
        )
        return pnl_pct


@dataclass
class MarketContext:
    price: float
    sell_balance_pct: float
    execution_strength: float
    now: datetime


class BrmEngine:
    def __init__(self, params: BrmParams, log_dir: Path | None = None) -> None:
        self.params = params
        self.book = BrmPaperBook()
        self._log_dir = log_dir or Path(__file__).resolve().parent.parent / "logs"
        self._log_path: Path | None = None

    def _in_session(self, now: datetime) -> bool:
        t = now.time()
        return self.params.t_session_start <= t < self.params.t_session_end

    def _allow_entry(self, now: datetime) -> bool:
        t = now.time()
        return self.params.t_session_start <= t < self.params.t_entry_cutoff

    def _must_flat(self, now: datetime) -> bool:
        return now.time() >= self.params.t_session_end

    def _hoga_ok(self, ctx: MarketContext, for_add: bool = False) -> bool:
        if for_add:
            min_sell = self.params.add_min_sell_balance_pct
            min_str = self.params.add_min_execution_strength
        else:
            min_sell = self.params.min_sell_balance_pct
            min_str = self.params.min_execution_strength
        if ctx.sell_balance_pct > 0 and ctx.sell_balance_pct < min_sell:
            return False
        if min_str > 0 and ctx.execution_strength > 0 and ctx.execution_strength < min_str:
            return False
        return True

    def _volume_ok(self, store: MinuteBarStore, now: datetime) -> bool:
        p = self.params
        sess_vol = store.session_volume(now)
        if p.min_session_volume > 0 and sess_vol < p.min_session_volume:
            return False
        if not p.require_volume_surge:
            return True
        vols = store.volumes()
        if len(vols) < 10:
            return True
        avg = sum(vols[-20:]) / min(20, len(vols))
        if avg <= 0:
            return True
        return vols[-1] >= avg * p.volume_surge_ratio

    def _spring_entry(self, store: MinuteBarStore) -> bool:
        p = self.params
        lows = store.lows()
        closes = store.closes()
        if len(lows) < p.low_depth + p.low_offset + 2:
            return False
        l_series = lowest(lows, p.low_depth)
        i = len(lows) - 1
        hl_idx = i - p.low_offset
        if hl_idx < 0:
            return False
        hl = l_series[hl_idx]
        if hl is None:
            return False
        return lows[i] < hl and closes[i] > hl

    def _indicator_snapshot(self, store: MinuteBarStore) -> dict:
        closes = store.closes()
        if len(closes) < 5:
            return {}
        r = rsi(closes, self.params.rsi_period)
        basis, upper, lower = bollinger(closes, self.params.bb_length, self.params.bb_mult)
        macd_line, signal, _hist = macd(
            closes,
            self.params.macd_fast,
            self.params.macd_slow,
            self.params.macd_signal,
        )
        i = len(closes) - 1
        prev = i - 1
        return {
            "rsi": r[i],
            "rsi_prev": r[prev] if prev >= 0 else None,
            "basis": basis[i],
            "upper": upper[i],
            "lower": lower[i],
            "upper_prev": upper[prev] if prev >= 0 else None,
            "high_prev": store.highs()[prev] if prev >= 0 else None,
            "macd": macd_line[i],
            "macd_prev": macd_line[prev] if prev >= 0 else None,
            "signal": signal[i],
            "signal_prev": signal[prev] if prev >= 0 else None,
            "close": closes[i],
            "open": store.bars[i].open if store.bars else closes[i],
            "bullish": store.bars[i].is_bullish if store.bars else False,
        }

    def evaluate(
        self,
        code: str,
        name: str,
        store: MinuteBarStore,
        ctx: MarketContext,
    ) -> BrmSignal:
        price = ctx.price
        snap = self._indicator_snapshot(store)
        base = BrmSignal(
            code=code,
            name=name,
            action=BrmAction.NONE,
            price=price,
            qty=0,
            reason="",
            rsi=snap.get("rsi"),
            sell_pct=ctx.sell_balance_pct,
            strength=ctx.execution_strength,
            session_vol=store.session_volume(ctx.now),
        )

        if price <= 0:
            return base

        if self._must_flat(ctx.now):
            pos = self.book.positions.get(code)
            if pos:
                return BrmSignal(
                    code=code,
                    name=name,
                    action=BrmAction.TIME_FLAT,
                    price=price,
                    qty=pos.qty,
                    reason="11:00 session end",
                    rsi=snap.get("rsi"),
                    sell_pct=ctx.sell_balance_pct,
                    strength=ctx.execution_strength,
                    session_vol=store.session_volume(ctx.now),
                )
            return base

        if not self._in_session(ctx.now):
            return base

        pos = self.book.positions.get(code)
        if pos:
            return self._evaluate_exit(code, name, pos, store, ctx, snap, base)

        if not self._allow_entry(ctx.now):
            return base
        if not self._hoga_ok(ctx):
            return base
        if not self._volume_ok(store, ctx.now):
            return base
        if not self._spring_entry(store):
            return base
        rsi_val = snap.get("rsi")
        if rsi_val is not None and rsi_val >= self.params.rsi_entry_max:
            return base

        qty = max(1, self.params.base_qty)
        return BrmSignal(
            code=code,
            name=name,
            action=BrmAction.ENTRY,
            price=price,
            qty=qty,
            reason="spring+RSI+hoga",
            rsi=rsi_val,
            sell_pct=ctx.sell_balance_pct,
            strength=ctx.execution_strength,
            session_vol=store.session_volume(ctx.now),
        )

    def _evaluate_exit(
        self,
        code: str,
        name: str,
        pos: BrmPaperPosition,
        store: MinuteBarStore,
        ctx: MarketContext,
        snap: dict,
        base: BrmSignal,
    ) -> BrmSignal:
        p = self.params
        price = ctx.price
        avg = pos.avg_price
        min_profit = avg * (1 + p.tp_min_profit_pct / 100.0)
        above_min = price > min_profit

        if price <= avg * (1 - p.stop_loss_pct / 100.0):
            return BrmSignal(
                code=code,
                name=name,
                action=BrmAction.STOP,
                price=price,
                qty=pos.qty,
                reason=f"stop -{p.stop_loss_pct}%",
                rsi=snap.get("rsi"),
                sell_pct=ctx.sell_balance_pct,
                strength=ctx.execution_strength,
                session_vol=store.session_volume(ctx.now),
            )

        if price >= avg * (1 + p.tp_pct / 100.0):
            return BrmSignal(
                code=code,
                name=name,
                action=BrmAction.TP,
                price=price,
                qty=pos.qty,
                reason=f"tp +{p.tp_pct}%",
                rsi=snap.get("rsi"),
                sell_pct=ctx.sell_balance_pct,
                strength=ctx.execution_strength,
                session_vol=store.session_volume(ctx.now),
            )

        rsi_val = snap.get("rsi")
        upper = snap.get("upper")
        upper_prev = snap.get("upper_prev")
        high_prev = snap.get("high_prev")
        basis = snap.get("basis")
        close = snap.get("close") or price

        if above_min and upper is not None and upper_prev is not None and high_prev is not None:
            if upper < high_prev and upper > close and basis is not None and basis < close:
                return BrmSignal(
                    code=code,
                    name=name,
                    action=BrmAction.B_EXIT,
                    price=price,
                    qty=pos.qty,
                    reason="BB exit",
                    rsi=rsi_val,
                    sell_pct=ctx.sell_balance_pct,
                    strength=ctx.execution_strength,
                    session_vol=store.session_volume(ctx.now),
                )

        if (
            above_min
            and rsi_val is not None
            and rsi_val > p.rsi_exit_min
            and not snap.get("bullish", True)
            and basis is not None
            and basis < close
        ):
            return BrmSignal(
                code=code,
                name=name,
                action=BrmAction.R_EXIT,
                price=price,
                qty=pos.qty,
                reason="RSI exit",
                rsi=rsi_val,
                sell_pct=ctx.sell_balance_pct,
                strength=ctx.execution_strength,
                session_vol=store.session_volume(ctx.now),
            )

        if above_min and basis is not None and basis < close:
            if crossed_under(
                snap.get("macd_prev"),
                snap.get("signal_prev"),
                snap.get("macd"),
                snap.get("signal"),
            ):
                return BrmSignal(
                    code=code,
                    name=name,
                    action=BrmAction.M_EXIT,
                    price=price,
                    qty=pos.qty,
                    reason="MACD exit",
                    rsi=rsi_val,
                    sell_pct=ctx.sell_balance_pct,
                    strength=ctx.execution_strength,
                    session_vol=store.session_volume(ctx.now),
                )

        if (
            pos.entries < p.max_entries
            and self._allow_entry(ctx.now)
            and self._hoga_ok(ctx, for_add=True)
            and price < avg * (1 - p.martin_trigger_pct / 100.0)
            and snap.get("bullish")
            and (rsi_val is None or rsi_val < p.rsi_add_max)
        ):
            add_qty = max(1, int(p.base_qty * (p.martin_ratio * pos.entries + 1)))
            return BrmSignal(
                code=code,
                name=name,
                action=BrmAction.ADD,
                price=price,
                qty=add_qty,
                reason=f"martin -{p.martin_trigger_pct}%",
                rsi=rsi_val,
                sell_pct=ctx.sell_balance_pct,
                strength=ctx.execution_strength,
                session_vol=store.session_volume(ctx.now),
            )

        return base

    def apply_signal(self, sig: BrmSignal, now: datetime) -> None:
        if sig.action == BrmAction.NONE:
            return
        if sig.action == BrmAction.ENTRY:
            self.book.open_or_add(sig.code, sig.name, sig.qty, sig.price, now, is_add=False)
        elif sig.action == BrmAction.ADD:
            self.book.open_or_add(sig.code, sig.name, sig.qty, sig.price, now, is_add=True)
        else:
            self.book.close(sig.code, sig.price, sig.action.value)
        self._log_signal(sig, now)

    def _log_signal(self, sig: BrmSignal, now: datetime) -> None:
        if not self.params.log_signals:
            return
        self._log_dir.mkdir(parents=True, exist_ok=True)
        if self._log_path is None or self._log_path.name != f"brm_paper_{now:%Y%m%d}.csv":
            self._log_path = self._log_dir / f"brm_paper_{now:%Y%m%d}.csv"
            if not self._log_path.exists():
                with self._log_path.open("w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(
                        [
                            "time",
                            "code",
                            "name",
                            "action",
                            "price",
                            "qty",
                            "reason",
                            "rsi",
                            "sell_pct",
                            "strength",
                            "session_vol",
                        ]
                    )
        with self._log_path.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    now.strftime("%H:%M:%S"),
                    sig.code,
                    sig.name,
                    sig.action.value,
                    f"{sig.price:.0f}",
                    sig.qty,
                    sig.reason,
                    f"{sig.rsi:.1f}" if sig.rsi is not None else "",
                    f"{sig.sell_pct:.1f}" if sig.sell_pct is not None else "",
                    f"{sig.strength:.1f}" if sig.strength is not None else "",
                    sig.session_vol,
                ]
            )
        logger.info(
            "BRM %s %s %s @%s qty=%s %s",
            sig.action.value,
            sig.code,
            sig.name,
            sig.price,
            sig.qty,
            sig.reason,
        )
