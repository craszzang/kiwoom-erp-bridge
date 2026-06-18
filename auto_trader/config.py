"""Config load/save."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from auto_trader.i18n_ko import MOCK_LOGIN_HINT


def normalize_account_no(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        return digits + "01"
    return digits


@dataclass
class TraderConfig:
    account_no: str = ""
    mock_account_no: str = ""
    real_account_no: str = ""
    mock_user_id: str = ""
    mock_mode: str = "catch"
    use_mock: bool = True
    screen_no: str = "0101"
    real_screen_no: str = "0102"
    tr_screen_no: str = "0103"
    condition_screen_no: str = "0150"
    watch_mode: str = "market"
    watch_codes: list[str] = field(default_factory=list)
    condition_name: str = ""
    condition_index: int = 0
    max_positions: int = 3
    order_qty: int = 1
    buy_drop_pct: float = 1.0
    sell_rise_pct: float = 1.5
    log_level: str = "INFO"
    min_sell_balance_pct: float = 50.0
    min_execution_strength: float = 100.0
    filter_pass_only: bool = False
    bridge_role: str = "host"
    bridge_host: str = ""
    bridge_port: int = 8765
    bridge_http_port: int = 8766
    bridge_token: str = ""
    bridge_auto_sync: bool = True
    update_source: str = "host"
    github_repo: str = ""
    github_branch: str = "main"
    github_mode: str = "manifest"
    github_asset: str = "client.zip"

    @property
    def active_account_no(self) -> str:
        if self.use_mock:
            return self.mock_account_no or self.account_no
        return self.real_account_no or self.account_no


def config_path(path: str | Path | None = None) -> Path:
    root = Path(__file__).resolve().parent.parent
    if path:
        return Path(path)
    cfg = root / "config.yaml"
    return cfg if cfg.exists() else root / "config.yaml.example"


def _read_yaml_file(cfg_file: Path) -> dict[str, Any]:
    data = cfg_file.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            text = data.decode(encoding)
            parsed = yaml.safe_load(text)
            return parsed if isinstance(parsed, dict) else {}
        except (UnicodeDecodeError, yaml.YAMLError):
            continue
    text = data.decode("utf-8", errors="replace")
    parsed = yaml.safe_load(text)
    return parsed if isinstance(parsed, dict) else {}


def load_config(path: str | Path | None = None) -> TraderConfig:
    cfg_file = config_path(path)
    if not cfg_file.exists():
        return TraderConfig()

    raw = _read_yaml_file(cfg_file)

    mock = raw.get("mock") or {}
    mock_account_no = str(mock.get("account_no", "")) if isinstance(mock, dict) else ""
    mock_user_id = str(mock.get("user_id", "")) if isinstance(mock, dict) else ""
    real = raw.get("real") or {}
    real_account_no = str(real.get("account_no", "")) if isinstance(real, dict) else ""
    mock_mode = str(raw.get("mock_mode", mock.get("mode", "catch") if isinstance(mock, dict) else "catch"))
    filters = raw.get("filters") or {}
    if not isinstance(filters, dict):
        filters = {}

    cfg = TraderConfig(
        account_no=normalize_account_no(str(raw.get("account_no", ""))),
        mock_account_no=normalize_account_no(mock_account_no) if mock_account_no else "",
        real_account_no=normalize_account_no(real_account_no) if real_account_no else "",
        mock_user_id=mock_user_id,
        mock_mode=mock_mode,
        use_mock=bool(raw.get("use_mock", True)),
        screen_no=str(raw.get("screen_no", "0101")),
        real_screen_no=str(raw.get("real_screen_no", "0102")),
        tr_screen_no=str(raw.get("tr_screen_no", "0103")),
        condition_screen_no=str(raw.get("condition_screen_no", "0150")),
        watch_mode=str(raw.get("watch_mode", "market")),
        watch_codes=list(raw.get("watch_codes", [])),
        condition_name=str(raw.get("condition_name", "")),
        condition_index=int(raw.get("condition_index", 0)),
        max_positions=int(raw.get("max_positions", 3)),
        order_qty=int(raw.get("order_qty", 1)),
        buy_drop_pct=float(raw.get("buy_drop_pct", 1.0)),
        sell_rise_pct=float(raw.get("sell_rise_pct", 1.5)),
        log_level=str(raw.get("log_level", "INFO")),
        min_sell_balance_pct=float(filters.get("min_sell_balance_pct", raw.get("min_sell_balance_pct", 50.0))),
        min_execution_strength=float(
            filters.get("min_execution_strength", raw.get("min_execution_strength", 100.0))
        ),
        filter_pass_only=bool(filters.get("filter_pass_only", raw.get("filter_pass_only", False))),
    )

    bridge = raw.get("bridge") or {}
    if isinstance(bridge, dict):
        cfg.bridge_role = str(bridge.get("role", cfg.bridge_role))
        cfg.bridge_host = str(bridge.get("host", cfg.bridge_host))
        cfg.bridge_port = int(bridge.get("port", cfg.bridge_port))
        cfg.bridge_http_port = int(bridge.get("http_port", cfg.bridge_http_port))
        cfg.bridge_token = str(bridge.get("token", cfg.bridge_token))
        cfg.bridge_auto_sync = bool(bridge.get("auto_sync", cfg.bridge_auto_sync))

    update = raw.get("update") or {}
    if isinstance(update, dict):
        cfg.update_source = str(update.get("source", cfg.update_source))
        cfg.github_repo = str(update.get("github_repo", cfg.github_repo))
        cfg.github_branch = str(update.get("github_branch", cfg.github_branch))
        cfg.github_mode = str(update.get("github_mode", cfg.github_mode))
        cfg.github_asset = str(update.get("github_asset", cfg.github_asset))

    return cfg


def save_config(config: TraderConfig, path: str | Path | None = None) -> Path:
    cfg_file = config_path(path)
    if cfg_file.name.endswith(".example"):
        cfg_file = cfg_file.parent / "config.yaml"

    data: dict[str, Any] = {}
    if cfg_file.exists():
        data = _read_yaml_file(cfg_file)

    data["use_mock"] = config.use_mock
    data["mock_mode"] = config.mock_mode
    data["account_no"] = config.account_no
    data["mock"] = {
        "mode": config.mock_mode,
        "account_no": config.mock_account_no,
        "user_id": config.mock_user_id,
    }
    data["real"] = {"account_no": config.real_account_no}
    data["filters"] = {
        "min_sell_balance_pct": config.min_sell_balance_pct,
        "min_execution_strength": config.min_execution_strength,
        "filter_pass_only": config.filter_pass_only,
    }
    data["bridge"] = {
        "role": config.bridge_role,
        "host": config.bridge_host,
        "port": config.bridge_port,
        "http_port": config.bridge_http_port,
        "token": config.bridge_token,
        "auto_sync": config.bridge_auto_sync,
    }
    data["update"] = {
        "source": config.update_source,
        "github_repo": config.github_repo,
        "github_branch": config.github_branch,
        "github_mode": config.github_mode,
        "github_asset": config.github_asset,
    }
    for k, v in (
        ("screen_no", config.screen_no),
        ("real_screen_no", config.real_screen_no),
        ("tr_screen_no", config.tr_screen_no),
        ("condition_screen_no", config.condition_screen_no),
        ("watch_mode", config.watch_mode),
        ("watch_codes", config.watch_codes),
        ("condition_name", config.condition_name),
        ("condition_index", config.condition_index),
        ("max_positions", config.max_positions),
        ("order_qty", config.order_qty),
        ("buy_drop_pct", config.buy_drop_pct),
        ("sell_rise_pct", config.sell_rise_pct),
        ("log_level", config.log_level),
    ):
        data.setdefault(k, v)

    with cfg_file.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return cfg_file
