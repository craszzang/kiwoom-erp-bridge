"""Telegram Bot API notifications."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    parse_mode: str = "HTML"

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "TelegramConfig":
        if not raw:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            bot_token=str(raw.get("bot_token", "")),
            chat_id=str(raw.get("chat_id", "")),
            parse_mode=str(raw.get("parse_mode", "HTML")),
        )


def _telegram_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config.telegram.yaml"


def load_telegram_config() -> TelegramConfig:
    """Load from config.telegram.yaml, then env vars."""
    cfg = TelegramConfig()
    path = _telegram_config_path()
    if path.is_file():
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                tg = raw.get("telegram") if "telegram" in raw else raw
                if isinstance(tg, dict):
                    cfg = TelegramConfig.from_dict(tg)
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("telegram config read failed: %s", exc)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if token:
        cfg.bot_token = token
    if chat:
        cfg.chat_id = chat
    if cfg.bot_token and cfg.chat_id:
        cfg.enabled = True
    return cfg


def send_message(text: str, cfg: TelegramConfig | None = None) -> bool:
    cfg = cfg or load_telegram_config()
    if not cfg.enabled or not cfg.bot_token or not cfg.chat_id:
        logger.warning("telegram disabled or missing token/chat_id")
        return False
    url = TELEGRAM_API.format(token=cfg.bot_token)
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": cfg.chat_id,
                "text": text[:4000],
                "parse_mode": cfg.parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            logger.error("telegram send failed: %s %s", resp.status_code, resp.text[:200])
            return False
        return True
    except requests.RequestException as exc:
        logger.error("telegram request error: %s", exc)
        return False


def send_session_report(message: str) -> bool:
    return send_message(message)
