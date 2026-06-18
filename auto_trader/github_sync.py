"""Pull program updates from GitHub (public repo, free)."""

from __future__ import annotations

import hashlib
import json
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Callable
from urllib.parse import quote

import requests

from auto_trader.bridge_protocol import BRIDGE_VERSION

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_cache_path(root: Path) -> Path:
    return root / ".github_sync_manifest.json"


def _parse_repo(repo: str) -> tuple[str, str]:
    repo = repo.strip().strip("/")
    if "github.com/" in repo:
        repo = repo.split("github.com/", 1)[1]
    repo = repo.removesuffix(".git")
    if "/" not in repo:
        raise ValueError(f"invalid github repo: {repo!r} (use owner/name)")
    owner, name = repo.split("/", 1)
    return owner, name


def _raw_url(owner: str, name: str, branch: str, rel_path: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{quote(rel_path, safe='/')}"


def fetch_release_asset(repo: str, asset_name: str, timeout: float = 60.0) -> bytes:
    owner, name = _parse_repo(repo)
    url = f"{GITHUB_API}/repos/{owner}/{name}/releases/latest"
    resp = requests.get(url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
    resp.raise_for_status()
    for asset in resp.json().get("assets") or []:
        if str(asset.get("name", "")).lower() == asset_name.lower():
            dl = requests.get(asset["browser_download_url"], timeout=timeout)
            dl.raise_for_status()
            return dl.content
    raise FileNotFoundError(f"release asset not found: {asset_name}")


def fetch_latest_release_zip(repo: str, asset_name: str = "client.zip", timeout: float = 60.0) -> bytes:
    return fetch_release_asset(repo, asset_name, timeout=timeout)


def sync_from_github(
    repo: str,
    root: Path,
    *,
    branch: str = "main",
    mode: str = "manifest",
    asset_name: str = "client.zip",
    timeout: float = 30.0,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Update client files from GitHub. Returns (updated_count, message)."""

    def _progress(msg: str) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    owner, name = _parse_repo(repo)

    if mode == "release_zip":
        _progress(f"GitHub 릴리스 다운로드...\n{owner}/{name}")
        try:
            data = fetch_latest_release_zip(repo, asset_name=asset_name, timeout=timeout)
        except Exception as exc:
            return 0, f"GitHub 릴리스 실패: {exc}"
        updated = 0
        with zipfile.ZipFile(BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = info.filename.replace("\\", "/")
                if not rel.startswith("auto_trader/"):
                    continue
                dest = root / rel
                content = zf.read(info)
                if dest.is_file() and hashlib.sha256(content).hexdigest() == _sha256_file(dest):
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
                updated += 1
        return updated, f"GitHub 릴리스 적용 {updated}개 파일"

    manifest_url = _raw_url(owner, name, branch, "sync/client_manifest.json")
    _progress(f"GitHub manifest...\n{owner}/{name}")
    remote = None
    try:
        resp = requests.get(manifest_url, timeout=timeout)
        if resp.status_code == 200:
            remote = resp.json()
    except Exception:
        remote = None

    if remote is None:
        try:
            _progress("릴리스 manifest 다운로드...")
            raw = fetch_release_asset(repo, "client_manifest.json", timeout=timeout)
            remote = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            return 0, f"GitHub manifest 실패: {exc}"

    if remote.get("bridge_version") != BRIDGE_VERSION:
        logger.warning("bridge version mismatch github=%s local=%s", remote.get("bridge_version"), BRIDGE_VERSION)

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
        remote_hash = str(meta.get("sha256", ""))
        if not remote_hash:
            continue
        dest = root / rel.replace("/", "\\") if "\\" in str(root) else root / rel
        if dest.is_file() and _sha256_file(dest) == remote_hash:
            local_cache[rel] = remote_hash
            continue
        if local_cache.get(rel) == remote_hash and dest.is_file():
            continue

        try:
            _progress(f"다운로드: {rel}")
            fr = requests.get(_raw_url(owner, name, branch, rel), timeout=timeout)
            fr.raise_for_status()
        except Exception as exc:
            logger.warning("github download failed %s: %s", rel, exc)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(fr.content)
        local_cache[rel] = remote_hash
        updated += 1

    cache_path.write_text(json.dumps(local_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    version = remote.get("bundle_version", "?")
    if updated:
        return updated, f"GitHub 업데이트 {updated}개 (v{version})"
    return 0, f"GitHub 최신 버전 (v{version})"
