"""Technical indicators for BRM (pure Python, no pandas)."""

from __future__ import annotations

import math
from typing import Sequence


def sma(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        out[i] = sum(window) / period
    return out


def ema(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def stdev(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 1:
        return out
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        out[i] = math.sqrt(var)
    return out


def rsi(closes: Sequence[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - (100.0 / (1.0 + rs))
    for i in range(period + 1, len(closes)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def bollinger(
    closes: Sequence[float], length: int = 200, mult: float = 1.5
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    basis = sma(closes, length)
    devs = stdev(closes, length)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if basis[i] is None or devs[i] is None:
            continue
        upper[i] = basis[i] + mult * devs[i]
        lower[i] = basis[i] - mult * devs[i]
    return basis, upper, lower


def macd(
    closes: Sequence[float],
    fast: int = 6,
    slow: int = 12,
    signal_period: int = 5,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast_ma = ema(closes, fast)
    slow_ma = ema(closes, slow)
    line: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if fast_ma[i] is not None and slow_ma[i] is not None:
            line[i] = fast_ma[i] - slow_ma[i]
    signal_input = [v if v is not None else 0.0 for v in line]
    first = next((i for i, v in enumerate(line) if v is not None), None)
    signal: list[float | None] = [None] * len(closes)
    hist: list[float | None] = [None] * len(closes)
    if first is None:
        return line, signal, hist
    segment = [line[i] for i in range(first, len(line)) if line[i] is not None]
    if len(segment) < signal_period:
        return line, signal, hist
    sig_seg = ema(segment, signal_period)
    idx = first
    for j, s in enumerate(sig_seg):
        if s is None:
            continue
        pos = first + j
        if pos < len(signal):
            signal[pos] = s
            if line[pos] is not None:
                hist[pos] = line[pos] - s
    return line, signal, hist


def lowest(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    for i in range(period - 1, len(values)):
        out[i] = min(values[i - period + 1 : i + 1])
    return out


def crossed_under(prev_a: float | None, prev_b: float | None, a: float | None, b: float | None) -> bool:
    if None in (prev_a, prev_b, a, b):
        return False
    return prev_a >= prev_b and a < b


def crossed_over(prev_a: float | None, prev_b: float | None, a: float | None, b: float | None) -> bool:
    if None in (prev_a, prev_b, a, b):
        return False
    return prev_a <= prev_b and a > b
