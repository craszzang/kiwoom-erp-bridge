"""5-minute bar load: sample, CSV, Kiwoom opt10080."""

from __future__ import annotations

import csv
import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto_trader.kiwoom_api import KiwoomAPI

logger = logging.getLogger(__name__)

F_BAR_TIME = "\uccb4\uacb0\uc2dc\uac04"
F_BAR_OPEN = "\uc2dc\uac00"
F_BAR_HIGH = "\uace0\uac00"
F_BAR_LOW = "\uc800\uac00"
F_BAR_CLOSE = "\ud604\uc7ac\uac00"
F_BAR_VOL = "\uac70\ub798\ub7c9"


@dataclass
class Bar5:
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
    return abs(float(text)) if text else 0.0


def _parse_int(raw: str) -> int:
    text = raw.strip().replace(",", "").lstrip("+-")
    return abs(int(text)) if text and text.isdigit() else int(abs(float(text or 0)))


def _parse_bar_time(trade_day: date, raw: str) -> datetime | None:
    text = raw.strip()
    if len(text) < 6:
        return None
    try:
        h, m, s = int(text[-6:-4]), int(text[-4:-2]), int(text[-2:])
        return datetime.combine(trade_day, time(h, m, s))
    except ValueError:
        return None


def load_csv(path: Path) -> list[Bar5]:
    rows: list[Bar5] = []
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt_s = row.get("datetime") or row.get("dt") or row.get("time") or ""
            if not dt_s:
                continue
            dt = datetime.fromisoformat(dt_s.replace(" ", "T")[:19])
            o = float(row.get("open", row.get("o", 0)))
            h = float(row.get("high", row.get("h", 0)))
            lo = float(row.get("low", row.get("l", 0)))
            c = float(row.get("close", row.get("c", 0)))
            v = int(float(row.get("volume", row.get("v", 0))))
            if c <= 0:
                continue
            rows.append(Bar5(dt=dt, open=o or c, high=h or c, low=lo or c, close=c, volume=v))
    rows.sort(key=lambda b: b.dt)
    return rows


def save_csv(path: Path, bars: list[Bar5]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["datetime", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow([b.dt.strftime("%Y-%m-%d %H:%M:%S"), b.open, b.high, b.low, b.close, b.volume])


def generate_sample_bars(
    code: str = "005930",
    *,
    seed: int = 42,
    base_price: float = 72000.0,
) -> list[Bar5]:
    """Synthetic intraday 5m bars (09:00~15:20) for offline backtest."""
    rng = random.Random(seed + hash(code) % 10000)
    day = date.today()
    if day.weekday() >= 5:
        day -= timedelta(days=day.weekday() - 4)

    bars: list[Bar5] = []
    price = base_price
    t = datetime.combine(day, time(9, 0))
    end = datetime.combine(day, time(15, 20))

    while t <= end:
        if t.time() < time(9, 0) or (time(12, 0) <= t.time() < time(12, 30)):
            t += timedelta(minutes=5)
            continue
        drift = rng.uniform(-0.004, 0.006)
        vol = int(rng.uniform(8000, 120000))
        o = price
        c = max(100.0, o * (1 + drift))
        h = max(o, c) * (1 + rng.uniform(0, 0.003))
        lo = min(o, c) * (1 - rng.uniform(0, 0.003))
        bars.append(Bar5(dt=t, open=o, high=h, low=lo, close=c, volume=vol))
        price = c
        t += timedelta(minutes=5)

    logger.info("generated %d sample 5m bars for %s", len(bars), code)
    return bars


def fetch_kiwoom_5m(
    api: "KiwoomAPI",
    code: str,
    screen_no: str,
    bar_minutes: int = 5,
    max_bars: int = 600,
) -> list[Bar5]:
    api.set_input_value("\uc885\ubaa9\ucf54\ub4dc", code)
    api.set_input_value("\ud2f1\ubc94\uc704", str(bar_minutes))
    api.set_input_value("\uc218\uc815\uc8fc\uac00\uad6c\ubd84", "1")
    rq = f"bt5_{code}"
    if api.comm_rq_data(rq, "opt10080", 0, screen_no) != 0:
        logger.error("opt10080 failed for %s", code)
        return []

    trade_day = date.today()
    rows: list[Bar5] = []
    limit = min(max_bars, 900)
    for i in range(limit):
        t_raw = api.get_comm_data("opt10080", rq, i, F_BAR_TIME)
        if not t_raw.strip():
            break
        dt = _parse_bar_time(trade_day, t_raw)
        if dt is None:
            continue
        c = _parse_price(api.get_comm_data("opt10080", rq, i, F_BAR_CLOSE))
        if c <= 0:
            continue
        o = _parse_price(api.get_comm_data("opt10080", rq, i, F_BAR_OPEN)) or c
        h = _parse_price(api.get_comm_data("opt10080", rq, i, F_BAR_HIGH)) or c
        lo = _parse_price(api.get_comm_data("opt10080", rq, i, F_BAR_LOW)) or c
        v = _parse_int(api.get_comm_data("opt10080", rq, i, F_BAR_VOL))
        rows.append(Bar5(dt=dt, open=o, high=h, low=lo, close=c, volume=v))

    rows.sort(key=lambda b: b.dt)
    if len(rows) > max_bars:
        rows = rows[-max_bars:]
    logger.info("kiwoom loaded %d x %sm bars for %s", len(rows), bar_minutes, code)
    return rows


def load_bars_for_code(
    code: str,
    *,
    source: str,
    csv_dir: Path,
    api: "KiwoomAPI | None" = None,
    screen_no: str = "0110",
    bar_minutes: int = 5,
    max_bars: int = 600,
) -> list[Bar5]:
    if source == "kiwoom":
        if api is None:
            raise RuntimeError("Kiwoom API required for source=kiwoom")
        return fetch_kiwoom_5m(api, code, screen_no, bar_minutes, max_bars)

    csv_path = csv_dir / f"{code}_{bar_minutes}m.csv"
    if source == "csv" or (source == "auto" and csv_path.is_file()):
        if not csv_path.is_file():
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        return load_csv(csv_path)

    bars = generate_sample_bars(code)
    save_csv(csv_path, bars)
    return bars
