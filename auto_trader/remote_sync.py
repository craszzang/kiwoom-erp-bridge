"""Pull project updates from host bridge HTTP server."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

import requests

from auto_trader import i18n_ko as T
from auto_trader.bridge_protocol import BRIDGE_VERSION

logger = logging.getLogger(__name__)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_cache_path(root: Path) -> Path:
    return root / ".bridge_sync_manifest.json"


def sync_from_host(
    base_url: str,
    root: Path,
    *,
    token: str = "",
    timeout: float = 8.0,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Download changed files. Returns (updated_count, message)."""
    headers = {"X-Bridge-Token": token} if token else {}

    def _progress(msg: str) -> None:
        logger.info(msg)
        if on_progress is not None:
            on_progress(msg)

    url = f"{base_url.rstrip('/')}/api/sync/manifest"
    try:
        _progress(T.REMOTE_SYNC_CONNECT_FMT.format(url=url))
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        return 0, T.REMOTE_SYNC_FAIL_FMT.format(exc=exc)

    remote = resp.json()
    if remote.get("bridge_version") != BRIDGE_VERSION:
        logger.warning(
            "bridge version mismatch host=%s client=%s",
            remote.get("bridge_version"),
            BRIDGE_VERSION,
        )

    files: dict[str, dict] = remote.get("files") or {}
    cache_path = _manifest_cache_path(root)
    local_cache: dict[str, str] = {}
    if cache_path.is_file():
        try:
            local_cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            local_cache = {}

    updated = 0
    for rel, meta in files.items():
        rel_path = rel.replace("/", "\\") if "\\" in str(root) else rel
        dest = root / rel_path
        remote_hash = str(meta.get("sha256", ""))
        if not remote_hash:
            continue
        if dest.is_file() and _sha256_file(dest) == remote_hash:
            local_cache[rel] = remote_hash
            continue
        if local_cache.get(rel) == remote_hash and dest.is_file():
            continue

        try:
            _progress(T.REMOTE_SYNC_DOWNLOAD_FMT.format(rel=rel))
            fr = requests.get(
                f"{base_url.rstrip('/')}/api/sync/file",
                params={"path": rel},
                headers=headers,
                timeout=timeout,
            )
            fr.raise_for_status()
        except Exception as exc:
            logger.warning("download failed %s: %s", rel, exc)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(fr.content)
        local_cache[rel] = remote_hash
        updated += 1
        logger.info("synced %s", rel)

    cache_path.write_text(json.dumps(local_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    version = remote.get("bundle_version", "?")
    if updated:
        return updated, T.REMOTE_SYNC_UPDATE_FMT.format(count=updated, version=version)
    return 0, T.REMOTE_SYNC_LATEST_FMT.format(version=version)
