"""Build client_manifest.json for GitHub auto-update."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auto_trader.bridge_protocol import BRIDGE_VERSION, SYNC_EXCLUDE, SYNC_GLOBS
OUT = ROOT / "sync" / "client_manifest.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest() -> dict:
    files: dict[str, dict] = {}
    bundle = hashlib.sha256()
    for pattern in SYNC_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in SYNC_EXCLUDE:
                continue
            digest = _sha256_file(path)
            bundle.update(rel.encode("utf-8"))
            bundle.update(digest.encode("ascii"))
            files[rel] = {"sha256": digest, "size": path.stat().st_size}
    return {
        "bridge_version": BRIDGE_VERSION,
        "bundle_version": bundle.hexdigest()[:12],
        "files": files,
    }


def main() -> None:
    manifest = build_manifest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(manifest['files'])} files, v{manifest['bundle_version']})")


if __name__ == "__main__":
    main()
