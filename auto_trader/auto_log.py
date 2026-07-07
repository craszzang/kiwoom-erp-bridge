"""File logging for silent automation mode."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_CONFIGURED = False


def setup_auto_logging(level: str = "INFO") -> Path:
    global _CONFIGURED
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / f"auto_{datetime.now():%Y%m%d}.log"
    if _CONFIGURED:
        return log_file

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    _CONFIGURED = True
    return log_file
