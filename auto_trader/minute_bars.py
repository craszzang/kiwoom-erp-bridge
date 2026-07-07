"""Minute bar feed: Kiwoom opt10080 + real-time tick updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Callable

from PyQt5.QtCore import QTimer

if TYPE_CHECKING:
    from auto_trader.kiwoom_api import KiwoomAPI

logger = logging.getLogger(__name__)

F_BAR_TIME = "\uccb4\uacb0\uc2dc\uac04"
F_BAR_OPEN = "\uc2dc\uac00"
F_BAR_HIGH = "\uace0\uac00"
F_BAR_LOW = "\uc800\uac00"
F_BAR_CLOSE = "\ud604\uc7ac\uac00"
F_BAR_VOL = "\uac70\ub798\ub7c9"
F_TICK_RANGE = "\ud2f1\ubc94\uc704"
F_ADJ = "\uc218\uc815\uc8fc\uac00\uad6c\ubd84"


@dataclass
class MinuteBar:
    dt: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open


def _parse_price(raw: str) -> float:
    text = raw.strip().replace(",", "").lstrip("+-")
    if not text:
        return 0.0
    try:
        return abs(float(text))
    except ValueError:
        return 0.0


def _parse_int(raw: str) -> int:
    text = raw.strip().replace(",", "").lstrip("+-")
    if not text:
        return 0
    try:
        return abs(int(text))
    except ValueError:
        return 0


def _parse_bar_time(trade_day: date, raw: str) -> datetime | None:
    text = raw.strip()
    if not text:
        return None
    if len(text) >= 6:
        try:
            h = int(text[-6:-4])
            m = int(text[-4:-2])
            s = int(text[-2:])
            return datetime.combine(trade_day, time(h, m, s))
        except ValueError:
            pass
    return None


@dataclass
class MinuteBarStore:
    code: str
    bars: list[MinuteBar] = field(default_factory=list)
    _cum_volume: int = 0
    _session_base_volume: int | None = None
    _session_day: date | None = None

    def session_volume(self, now: datetime) -> int:
        if self._session_day != now.date():
            self._session_day = now.date()
            self._session_base_volume = self._cum_volume
        if self._session_base_volume is None:
            return 0
        return max(0, self._cum_volume - self._session_base_volume)

    def reset_session_volume(self, now: datetime, cum_volume: int) -> None:
        self._session_day = now.date()
        self._session_base_volume = cum_volume
        self._cum_volume = cum_volume

    def update_cum_volume(self, cum_volume: int, now: datetime) -> None:
        if cum_volume <= 0:
            return
        if self._session_day != now.date():
            self.reset_session_volume(now, cum_volume)
        self._cum_volume = cum_volume

    def ingest_history(self, rows: list[MinuteBar]) -> None:
        if not rows:
            return
        merged = {b.dt: b for b in self.bars}
        for b in rows:
            merged[b.dt] = b
        self.bars = sorted(merged.values(), key=lambda x: x.dt)
        if self.bars:
            last = self.bars[-1]
            self._cum_volume = sum(b.volume for b in self.bars)

    def update_tick(self, price: float, now: datetime, tick_volume: int = 0) -> None:
        if price <= 0:
            return
        minute = now.replace(second=0, microsecond=0)
        if self.bars and self.bars[-1].dt == minute:
            bar = self.bars[-1]
            bar.high = max(bar.high, price)
            bar.low = min(bar.low, price)
            bar.close = price
            if tick_volume > 0:
                bar.volume += tick_volume
            return
        self.bars.append(
            MinuteBar(
                dt=minute,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=max(0, tick_volume),
            )
        )
        if len(self.bars) > 500:
            self.bars = self.bars[-500:]

    def closes(self) -> list[float]:
        return [b.close for b in self.bars]

    def highs(self) -> list[float]:
        return [b.high for b in self.bars]

    def lows(self) -> list[float]:
        return [b.low for b in self.bars]

    def volumes(self) -> list[int]:
        return [b.volume for b in self.bars]


class MinuteBarLoader:
    """Loads opt10080 history with Kiwoom TR rate limiting."""

    def __init__(self, api: "KiwoomAPI", screen_no: str, bar_minutes: int = 1) -> None:
        self.api = api
        self.screen_no = screen_no
        self.bar_minutes = bar_minutes
        self._queue: list[str] = []
        self._stores: dict[str, MinuteBarStore] = {}
        self._on_done: Callable[[], None] | None = None

    def store(self, code: str) -> MinuteBarStore:
        st = self._stores.get(code)
        if st is None:
            st = MinuteBarStore(code=code)
            self._stores[code] = st
        return st

    def stores(self) -> dict[str, MinuteBarStore]:
        return self._stores

    def enqueue(self, codes: list[str], on_done: Callable[[], None] | None = None) -> None:
        self._queue = list(dict.fromkeys(codes))
        self._on_done = on_done
        QTimer.singleShot(0, self._step)

    def _step(self) -> None:
        if not self._queue:
            if self._on_done:
                self._on_done()
            return
        code = self._queue.pop(0)
        try:
            self._fetch(code)
        except Exception as exc:
            logger.warning("minute bars %s failed: %s", code, exc)
        QTimer.singleShot(280, self._step)

    def _fetch(self, code: str) -> None:
        self.api.set_input_value("\uc885\ubaa9\ucf54\ub4dc", code)
        self.api.set_input_value(F_TICK_RANGE, str(self.bar_minutes))
        self.api.set_input_value(F_ADJ, "1")
        rq = f"min_{code}"
        if self.api.comm_rq_data(rq, "opt10080", 0, self.screen_no) != 0:
            return
        trade_day = date.today()
        rows: list[MinuteBar] = []
        for i in range(200):
            t_raw = self.api.get_comm_data("opt10080", rq, i, F_BAR_TIME)
            if not t_raw.strip():
                break
            dt = _parse_bar_time(trade_day, t_raw)
            if dt is None:
                continue
            o = _parse_price(self.api.get_comm_data("opt10080", rq, i, F_BAR_OPEN))
            h = _parse_price(self.api.get_comm_data("opt10080", rq, i, F_BAR_HIGH))
            lo = _parse_price(self.api.get_comm_data("opt10080", rq, i, F_BAR_LOW))
            c = _parse_price(self.api.get_comm_data("opt10080", rq, i, F_BAR_CLOSE))
            v = _parse_int(self.api.get_comm_data("opt10080", rq, i, F_BAR_VOL))
            if c <= 0:
                continue
            rows.append(MinuteBar(dt=dt, open=o or c, high=h or c, low=lo or c, close=c, volume=v))
        if rows:
            rows.sort(key=lambda b: b.dt)
            self.store(code).ingest_history(rows)
            logger.info("loaded %d minute bars for %s", len(rows), code)
