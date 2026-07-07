"""Backtest report JSON + console summary."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .config_load import BacktestConfig
from .engine import BacktestResult

logger = logging.getLogger(__name__)


def print_summary(results: list[BacktestResult], cfg: BacktestConfig) -> None:
    print()
    print("=" * 56)
    print("  5분봉 백테스트 결과")
    print(f"  source={cfg.source}  bars={cfg.bar_minutes}m")
    print("=" * 56)
    total_pnl = 0.0
    total_exits = 0
    for r in results:
        s = r.stats
        pnl = float(s.get("realized_pnl", 0))
        total_pnl += pnl
        total_exits += int(s.get("exits", 0))
        print(f"\n[{r.code}] {r.name}  ({r.bar_count}봉)")
        print(f"  진입 {s.get('entries',0)}  청산 {s.get('exits',0)}  "
              f"승 {s.get('wins',0)} / 패 {s.get('losses',0)}  "
              f"승률 {s.get('win_rate',0)}%")
        print(f"  실현손익(모의): {pnl:+,.0f}")
        for t in r.trades[:5]:
            print(f"    - {t.get('name','')} {t.get('pnl_pct',0):+.2f}% ({t.get('reason','')})")
    print("\n" + "-" * 56)
    print(f"  합계 손익(모의): {total_pnl:+,.0f}  |  총 청산 {total_exits}건")
    print("=" * 56)
    print()


def save_report(results: list[BacktestResult], cfg: BacktestConfig) -> Path:
    out_dir = cfg.report_path
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"report_{stamp}.json"
    payload = {
        "generated_at": datetime.now().isoformat(),
        "source": cfg.source,
        "bar_minutes": cfg.bar_minutes,
        "daily_params": cfg.daily.to_dict(),
        "results": [
            {
                "code": r.code,
                "name": r.name,
                "bar_count": r.bar_count,
                "stats": r.stats,
                "trades": r.trades,
                "signals": r.signals,
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("report saved: %s", path)
    return path
