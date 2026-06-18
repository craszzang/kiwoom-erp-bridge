"""Remote client entry: sync updates from host then launch Excel UI."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_FILE = ROOT / "remote_launch.log"


def _log(msg: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


def _fatal(title: str, message: str) -> int:
    _log(f"FATAL: {title}: {message}")
    try:
        import auto_trader.qt_fix  # noqa: F401
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Critical)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.exec_()
    except Exception:
        print(f"{title}\n{message}", file=sys.stderr)
    return 1


def _resolve_host(config, args) -> str:
    from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox

    from auto_trader import i18n_ko as T

    host = (args.host or config.bridge_host or "").strip().strip("'\"")
    if not host:
        if sys.stdin.isatty():
            host = input(f"{T.REMOTE_BRIDGE_IP_PROMPT} ").strip()
        else:
            app = QApplication.instance() or QApplication([])
            text, ok = QInputDialog.getText(
                None,
                T.MSG_ERP_TITLE,
                T.REMOTE_BRIDGE_IP_PROMPT,
                text="192.168.0.11",
            )
            if ok and text.strip():
                host = text.strip()
    if not host:
        QMessageBox.warning(None, T.MSG_ERP_TITLE, T.REMOTE_HOST_CONFIG_WARN)
        return ""
    return host


def main() -> int:
    import auto_trader.qt_fix  # noqa: F401

    from PyQt5.QtWidgets import QApplication

    from auto_trader import i18n_ko as T
    from auto_trader.config import load_config
    from auto_trader.excel_ui import run_excel_ui
    from auto_trader.remote_startup import RemoteStartupSplash
    from auto_trader.remote_sync import sync_from_host

    _log("remote_main start")
    app = QApplication.instance() or QApplication([])
    splash = RemoteStartupSplash()
    splash.set_status(T.REMOTE_PREPARE)
    splash.show()

    parser = argparse.ArgumentParser(description="Remote Excel UI client")
    parser.add_argument("--host", help="Bridge host IP")
    parser.add_argument("--port", type=int, default=0, help="Bridge WS port")
    parser.add_argument("--http-port", type=int, default=0, help="Bridge HTTP port")
    parser.add_argument("--no-sync", action="store_true", help="Skip auto-update")
    args = parser.parse_args()

    config = load_config()
    splash.set_status(T.REMOTE_CONFIG_READ)
    host = _resolve_host(config, args)
    if not host:
        splash.close()
        return 1

    http_port = args.http_port or int(config.bridge_http_port or 0) or (int(config.bridge_port or 8765) + 1)
    base_url = f"http://{host}:{http_port}"
    _log(f"host={host} http_port={http_port}")

    if not args.no_sync:
        sync_msg = ""
        if config.update_source == "github" and config.github_repo.strip():
            from auto_trader.github_sync import sync_from_github

            count, sync_msg = sync_from_github(
                config.github_repo.strip(),
                ROOT,
                branch=config.github_branch,
                mode=config.github_mode,
                asset_name=config.github_asset,
                timeout=30.0,
                on_progress=splash.set_status,
            )
        elif config.bridge_auto_sync:
            count, sync_msg = sync_from_host(
                base_url,
                ROOT,
                token=config.bridge_token,
                timeout=8.0,
                on_progress=splash.set_status,
            )
        if sync_msg:
            _log(f"sync: {sync_msg}")
            splash.set_status(sync_msg + "\n\n" + T.REMOTE_OPEN_UI)
        else:
            splash.set_status(T.REMOTE_HOST_FMT.format(host=host) + T.REMOTE_OPEN_UI)
    else:
        splash.set_status(T.REMOTE_HOST_FMT.format(host=host) + T.REMOTE_OPEN_UI)

    config.bridge_role = "client"
    config.bridge_host = host
    if args.port:
        config.bridge_port = args.port

    splash.close()
    return run_excel_ui(config=config, remote=True)


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        tb = traceback.format_exc()
        _log(tb)
        from auto_trader import i18n_ko as T

        code = _fatal(T.REMOTE_FATAL_TITLE, f"{tb}\n\nlog: {LOG_FILE}")
    if code != 0:
        try:
            from auto_trader import i18n_ko as T

            input(T.REMOTE_ENTER_CLOSE)
        except EOFError:
            pass
    raise SystemExit(code)
