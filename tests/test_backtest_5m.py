"""Backtest engine tests (no Kiwoom)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_trader.daily_params import DailyParams
from backtest_5m.bars import generate_sample_bars, load_csv, save_csv
from backtest_5m.config_load import load_backtest_config
from backtest_5m.engine import run_backtest_on_bars


def test_sample_backtest_runs() -> None:
    bars = generate_sample_bars("005930", seed=1)
    assert len(bars) > 50
    params = DailyParams(min_execution_strength=90.0, min_sell_balance_pct=50.0)
    r = run_backtest_on_bars("005930", "Samsung", bars, params)
    assert r.bar_count == len(bars)
    assert "entries" in r.stats


def test_csv_roundtrip(tmp_path: Path | None = None) -> None:
    import tempfile

    d = tmp_path or Path(tempfile.mkdtemp())
    p = d / "005930_5m.csv"
    bars = generate_sample_bars("005930", seed=2)
    save_csv(p, bars)
    loaded = load_csv(p)
    assert len(loaded) == len(bars)


def test_config_loads() -> None:
    cfg = load_backtest_config(ROOT / "backtest_5m" / "config.backtest.yaml")
    assert cfg.bar_minutes == 5
    assert cfg.source == "sample"


if __name__ == "__main__":
    test_config_loads()
    test_sample_backtest_runs()
    test_csv_roundtrip()
    print("ALL OK")
