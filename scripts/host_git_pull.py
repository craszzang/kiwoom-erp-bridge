"""Git pull on host PC before autonomous trading (ff-only)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def git_pull_ff(root: Path | None = None) -> tuple[bool, str]:
    root = root or Path(__file__).resolve().parent.parent
    if not (root / ".git").is_dir():
        return False, "not a git repo"
    try:
        r = subprocess.run(
            ["git", "pull", "--ff-only", "origin", "main"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            logger.warning("git pull failed: %s", out.strip())
            return False, out.strip() or f"exit {r.returncode}"
        logger.info("git pull ok: %s", out.strip())
        return True, out.strip()
    except Exception as exc:
        logger.warning("git pull error: %s", exc)
        return False, str(exc)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ok, msg = git_pull_ff()
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
