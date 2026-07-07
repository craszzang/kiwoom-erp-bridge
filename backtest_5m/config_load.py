"""Load backtest_5m/config.backtest.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from auto_trader.daily_params import DailyParams

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CFG = Path(__file__).resolve().parent / "config.backtest.yaml"


@dataclass
class BacktestConfig:
    source: str = "sample"
    codes: list[str] = field(default_factory=lambda: ["005930"])
    csv_dir: str = "data/backtest"
    bar_minutes: int = 5
    kiwoom_screen_no: str = "0110"
    max_bars: int = 600
    daily: DailyParams = field(default_factory=DailyParams)
    report_dir: str = "logs/backtest"

    @property
    def csv_path(self) -> Path:
        return ROOT / self.csv_dir

    @property
    def report_path(self) -> Path:
        return ROOT / self.report_dir


def load_backtest_config(path: Path | None = None) -> BacktestConfig:
    cfg_file = path or DEFAULT_CFG
    if not cfg_file.is_file():
        return BacktestConfig()

    raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return BacktestConfig()

    daily_raw = raw.get("daily") or {}
    return BacktestConfig(
        source=str(raw.get("source", "sample")),
        codes=[str(c) for c in raw.get("codes", ["005930"])],
        csv_dir=str(raw.get("csv_dir", "data/backtest")),
        bar_minutes=int(raw.get("bar_minutes", 5)),
        kiwoom_screen_no=str(raw.get("kiwoom_screen_no", "0110")),
        max_bars=int(raw.get("max_bars", 600)),
        daily=DailyParams.from_dict(daily_raw if isinstance(daily_raw, dict) else {}),
        report_dir=str(raw.get("report_dir", "logs/backtest")),
    )
