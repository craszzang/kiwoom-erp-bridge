# -*- coding: utf-8 -*-
"""5-minute bar backtest CLI."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auto_trader.qt_fix  # noqa: F401

from backtest_5m.bars import load_bars_for_code
from backtest_5m.config_load import DEFAULT_CFG, load_backtest_config
from backtest_5m.engine import run_backtest_on_bars
from backtest_5m.report import print_summary, save_report


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _resolve_name(code: str, api) -> str:
    if api is None:
        return code
    try:
        return api.get_master_code_name(code) or code
    except Exception:
        return code


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    logger = logging.getLogger("backtest_5m")

    parser = argparse.ArgumentParser(description="5-minute bar backtester")
    parser.add_argument("--config", type=Path, default=DEFAULT_CFG, help="config.backtest.yaml path")
    parser.add_argument("--source", choices=["sample", "csv", "kiwoom"], help="override data source")
    parser.add_argument("--code", action="append", help="stock code (repeatable)")
    args = parser.parse_args(argv)

    cfg = load_backtest_config(args.config)
    if args.source:
        cfg.source = args.source
    codes = args.code or cfg.codes

    api = None
    if cfg.source == "kiwoom":
        from PyQt5.QtWidgets import QApplication

        from auto_trader.kiwoom_api import KiwoomAPI

        app = QApplication.instance() or QApplication(sys.argv)
        api = KiwoomAPI()
        err = api.comm_connect()
        if err != 0 or not api.is_connected():
            logger.error("Kiwoom login failed err=%s", err)
            return 1
        logger.info("Kiwoom connected")

    results = []
    for code in codes:
        code = code.strip()
        if not code:
            continue
        try:
            bars = load_bars_for_code(
                code,
                source=cfg.source,
                csv_dir=cfg.csv_path,
                api=api,
                screen_no=cfg.kiwoom_screen_no,
                bar_minutes=cfg.bar_minutes,
                max_bars=cfg.max_bars,
            )
        except Exception as exc:
            logger.error("%s load failed: %s", code, exc)
            continue
        name = _resolve_name(code, api)
        logger.info("%s: running backtest on %d bars", code, len(bars))
        results.append(run_backtest_on_bars(code, name, bars, cfg.daily))

    if not results:
        logger.error("no results — check codes / data source")
        return 2

    print_summary(results, cfg)
    report_path = save_report(results, cfg)
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
