"""Bridge protocol version and sync file patterns."""

from __future__ import annotations

BRIDGE_VERSION = "1.0.0"
DEFAULT_BRIDGE_PORT = 8765
DEFAULT_HTTP_PORT = 8766

# Client pulls these paths from host on startup (auto-update).
SYNC_GLOBS = (
    "auto_trader/*.py",
    "config.yaml.example",
)

# Host-only modules (not required on client, but harmless if synced).
SYNC_EXCLUDE = frozenset(
    {
        "auto_trader/bridge_host_main.py",
    }
)
