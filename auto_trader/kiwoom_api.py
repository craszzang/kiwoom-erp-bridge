"""Kiwoom OpenAPI wrapper (PyQt5 QAxWidget)."""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication

KIWOOM_DIR = Path(r"C:\OpenAPI")
OCX_FILE = KIWOOM_DIR / "khopenapi.ocx"
OPSTARTER = KIWOOM_DIR / "opstarter.exe"
PROG_ID = "KHOPENAPI.KHOpenAPICtrl.1"
CLSID = "{A1574A0D-6BFA-4BD7-9020-DED88711818D}"
COM_EVENTS = (
    "OnEventConnect",
    "OnReceiveTrData",
    "OnReceiveRealData",
    "OnReceiveChejanData",
    "OnReceiveTrCondition",
    "OnReceiveRealCondition",
    "OnReceiveConditionVer",
)


def _ensure_qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def _check_python_bitness() -> None:
    if struct.calcsize("P") * 8 != 32:
        raise RuntimeError(
            "Python must be 32-bit for Kiwoom OpenAPI.\n"
            "Use setup_env.bat / .venv32, not 64-bit Python."
        )


def _setup_kiwoom_dll_path() -> None:
    if not KIWOOM_DIR.is_dir():
        return
    kdir = str(KIWOOM_DIR)
    os.environ["PATH"] = kdir + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(kdir)


def _ensure_opstarter() -> None:
    if not OPSTARTER.is_file():
        return
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq opstarter.exe"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="cp949",
            errors="ignore",
        )
        if "opstarter.exe" in out.lower():
            return
    except Exception:
        pass
    try:
        subprocess.Popen(
            [str(OPSTARTER)],
            cwd=str(KIWOOM_DIR),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        time.sleep(2)
    except Exception:
        pass


def _register_ocx_silent() -> bool:
    regsvr = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64" / "regsvr32.exe"
    if not regsvr.is_file() or not OCX_FILE.is_file():
        return False
    try:
        r = subprocess.run(
            [str(regsvr), "/s", str(OCX_FILE)],
            cwd=str(KIWOOM_DIR),
            capture_output=True,
            timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def _clsid_registered() -> bool:
    try:
        r = subprocess.run(
            ["reg", "query", rf"HKCR\CLSID\{CLSID}"],
            capture_output=True,
            timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def normalize_stock_code(code: str) -> str:
    c = code.strip()
    if len(c) > 1 and c[0].upper() == "A":
        return c[1:]
    return c


def parse_condition_code_list(raw: str) -> list[str]:
    items: list[str] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if "^" in part:
            part = part.split("^", 1)[0].strip()
        code = normalize_stock_code(part)
        if code:
            items.append(code)
    return items


def fix_kiwoom_text(value: str) -> str:
    """Fix CP949 mojibake from Kiwoom COM/QAxWidget strings."""
    if not value:
        return value
    text = value.strip()
    if any("\uac00" <= ch <= "\ud7a3" for ch in text):
        return text
    try:
        raw = text.encode("latin1")
    except UnicodeEncodeError:
        return text
    for enc in ("cp949", "euc-kr"):
        try:
            fixed = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if any("\uac00" <= ch <= "\ud7a3" for ch in fixed):
            return fixed.strip()
    return text


def parse_condition_list(raw: str) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part or "^" not in part:
            continue
        idx_s, name = part.split("^", 1)
        try:
            items.append((int(idx_s), fix_kiwoom_text(name.strip())))
        except ValueError:
            continue
    return items


class KiwoomAPI(QAxWidget):
    def __init__(self) -> None:
        _check_python_bitness()
        _setup_kiwoom_dll_path()
        _ensure_qapp()
        super().__init__()
        self._login_loop: QEventLoop | None = None
        self._login_err: int = 0
        self._tr_loop: QEventLoop | None = None
        self._condition_loop: QEventLoop | None = None
        self._condition_codes: list[str] = []
        self._on_receive_real_data: Callable[[str, str, str], None] | None = None
        self._on_receive_real_condition: Callable[[str, str, str, str], None] | None = None
        self._on_receive_chejan: Callable[[str, int, str], None] | None = None
        self._login_poll_timer: QTimer | None = None
        self._events_wired = False
        self._set_control()
        self._wire_events()

    @staticmethod
    def _has_com_events(widget: QAxWidget) -> bool:
        try:
            signal = getattr(widget, "OnEventConnect")
        except AttributeError:
            return False
        return hasattr(signal, "connect")

    def _try_set_control(self, control: str) -> bool:
        self.clear()
        self.setControl(control)
        QApplication.processEvents()
        try:
            self.createHostWindow(False)
        except Exception:
            pass
        QApplication.processEvents()
        return not self.isNull() and self._has_com_events(self)

    def _set_control(self) -> None:
        if not OCX_FILE.is_file():
            raise RuntimeError(
                f"OCX not found: {OCX_FILE}\n"
                "Install Kiwoom OpenAPI+ from kiwoom.com (default C:\\OpenAPI)."
            )

        _register_ocx_silent()

        for control in (PROG_ID, CLSID):
            if self._try_set_control(control):
                return

        if not _clsid_registered():
            raise RuntimeError(
                "Kiwoom OCX registry broken (CLSID missing or wrong path).\n\n"
                "Often: old KK\\OpenAPI copy in OneDrive.\n\n"
                "Fix:\n"
                "1) C:\\OpenAPI\\fix_kiwoom_registry.bat (Administrator)\n"
                "2) C:\\OpenAPI\\run_ocx_test.bat\n"
                "3) Restart Excel UI"
            )

        raise RuntimeError(
            "Kiwoom OCX load failed.\n\n"
            f"Python: {sys.executable}\n"
            f"OCX: {OCX_FILE}\n\n"
            "Run C:\\OpenAPI\\fix_kiwoom_registry.bat as Administrator, then retry."
        )

    def _wire_events(self) -> None:
        if not self._has_com_events(self):
            return
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveRealData.connect(self._receive_real_data)
        self.OnReceiveChejanData.connect(self._receive_chejan_data)
        self.OnReceiveTrCondition.connect(self._receive_tr_condition)
        self.OnReceiveRealCondition.connect(self._receive_real_condition)
        self.OnReceiveConditionVer.connect(self._receive_condition_ver)
        self._events_wired = True

    def comm_connect(self, block: bool = True) -> int:
        """Return OnEventConnect err_code (0 = login success)."""
        self._login_err = 0
        self.dynamicCall("CommConnect()")
        if not block:
            return 0
        if self._events_wired:
            self._login_loop = QEventLoop()
            self._login_loop.exec_()
            return self._login_err

        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(300)

        def poll() -> None:
            if self.get_connect_state() == 1:
                loop.quit()

        timer.timeout.connect(poll)
        timer.start()
        loop.exec_()
        timer.stop()
        return 0 if self.get_connect_state() == 1 else -1

    def _event_connect(self, err_code: int) -> None:
        self._login_err = int(err_code)
        if self._login_loop is not None and self._login_loop.isRunning():
            self._login_loop.exit()

    def get_connect_state(self) -> int:
        return int(self.dynamicCall("GetConnectState()"))

    def is_connected(self) -> bool:
        return self.get_connect_state() == 1

    @staticmethod
    def login_error_text(err_code: int) -> str:
        messages = {
            0: "OK",
            -100: "login failed (ID/password)",
            -101: "server communication failed",
            -102: " version upgrade required",
            -106: "socket closed",
        }
        detail = messages.get(err_code, "unknown error")
        return f"code {err_code}: {detail}"

    def get_login_info(self, tag: str) -> str:
        return fix_kiwoom_text(str(self.dynamicCall("GetLoginInfo(QString)", tag)))

    def get_master_code_name(self, code: str) -> str:
        return fix_kiwoom_text(
            str(self.dynamicCall("GetMasterCodeName(QString)", normalize_stock_code(code)))
        ).strip()

    def get_master_last_price(self, code: str) -> int:
        raw = str(
            self.dynamicCall("GetMasterLastPrice(QString)", normalize_stock_code(code))
        ).strip()
        raw = raw.replace(",", "").lstrip("+-")
        try:
            return abs(int(raw))
        except ValueError:
            return 0

    def get_code_list_by_market(self, market: str) -> list[str]:
        """market: 0=KOSPI, 10=KOSDAQ, 8=KONEX, 3=ELW, ..."""
        raw = str(self.dynamicCall("GetCodeListByMarket(QString)", market)).strip()
        if not raw:
            return []
        return [normalize_stock_code(c) for c in raw.split(";") if c.strip()]

    def get_all_stock_codes(self) -> list[str]:
        codes: list[str] = []
        for market in ("0", "10"):
            codes.extend(self.get_code_list_by_market(market))
        return list(dict.fromkeys(c for c in codes if c))

    def koa_functions(self, name: str, param: str = "") -> str:
        return str(self.dynamicCall("KOA_Functions(QString, QString)", name, param))

    def show_account_password_window(self) -> None:
        """Open Kiwoom account-password registration dialog (required before orders)."""
        self.koa_functions("ShowAccountWindow", "")

    def get_condition_name_list(self) -> list[tuple[int, str]]:
        self.get_condition_load()
        raw = str(self.dynamicCall("GetConditionNameList()"))
        return parse_condition_list(raw)

    def get_accounts(self) -> list[str]:
        raw = self.get_login_info("ACCNO")
        return [a.strip() for a in raw.split(";") if a.strip()]

    def set_input_value(self, item: str, value: str) -> None:
        self.dynamicCall("SetInputValue(QString, QString)", item, value)

    def comm_rq_data(
        self, rq_name: str, tr_code: str, prev_next: int, screen_no: str, block: bool = True
    ) -> int:
        if block and not self._events_wired:
            raise RuntimeError(
                "TR request needs OnReceiveTrData event. "
                "Run register_kiwoom_ocx_admin.bat as Administrator."
            )
        ret = int(
            self.dynamicCall(
                "CommRqData(QString, QString, int, QString)",
                rq_name,
                tr_code,
                prev_next,
                screen_no,
            )
        )
        if block and ret == 0:
            self._tr_loop = QEventLoop()
            self._tr_loop.exec_()
        return ret

    def _receive_tr_data(self, *args) -> None:
        if self._tr_loop is not None and self._tr_loop.isRunning():
            self._tr_loop.exit()

    def get_comm_data(self, tr_code: str, rq_name: str, index: int, item: str) -> str:
        value = self.dynamicCall(
            "GetCommData(QString, QString, int, QString)", tr_code, rq_name, index, item
        )
        return fix_kiwoom_text(str(value).strip())

    def send_order(
        self,
        rq_name: str,
        screen_no: str,
        acc_no: str,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        hoga_gb: str,
        org_order_no: str = "",
    ) -> int:
        # PyQt5 QAxWidget: 9?? ????? ??????? ??????? TypeError ????
        args = [rq_name, screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no]
        ret = self.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            args,
        )
        return int(ret) if ret is not None else -1

    def set_real_reg(self, screen_no: str, codes: str, fids: str, opt_type: str) -> int:
        return int(
            self.dynamicCall(
                "SetRealReg(QString, QString, QString, QString)", screen_no, codes, fids, opt_type
            )
        )

    def register_real_callback(self, callback: Callable[[str, str, str], None] | None) -> None:
        self._on_receive_real_data = callback

    def _receive_real_data(self, code: str, real_type: str, real_data: str) -> None:
        if self._on_receive_real_data is not None:
            self._on_receive_real_data(
                normalize_stock_code(code),
                fix_kiwoom_text(real_type),
                real_data,
            )

    def get_comm_real_data(self, code: str, fid: int) -> str:
        c = normalize_stock_code(code)
        raw = str(self.dynamicCall("GetCommRealData(QString, int)", c, fid)).strip()
        if raw:
            return raw
        if not code.startswith("A"):
            return str(self.dynamicCall("GetCommRealData(QString, int)", f"A{c}", fid)).strip()
        return raw

    def register_chejan_callback(self, callback: Callable[[str, int, str], None] | None) -> None:
        self._on_receive_chejan = callback

    def _receive_chejan_data(self, gubun: str, item_cnt: int, fid_list: str) -> None:
        if self._on_receive_chejan is not None:
            self._on_receive_chejan(gubun, item_cnt, fid_list)

    def get_chejan_data(self, fid: int) -> str:
        return str(self.dynamicCall("GetChejanData(int)", fid)).strip()

    def get_condition_load(self, block: bool = True) -> int:
        if block and not self._events_wired:
            raise RuntimeError(
                "Condition load needs COM events. "
                "Run register_kiwoom_ocx_admin.bat as Administrator."
            )
        ret = int(self.dynamicCall("GetConditionLoad()"))
        if block and ret == 1:
            self._condition_loop = QEventLoop()
            self._condition_loop.exec_()
        return ret

    def _receive_condition_ver(self, ret: int, msg: str) -> None:
        if self._condition_loop is not None and self._condition_loop.isRunning():
            self._condition_loop.exit()

    def register_real_condition_callback(
        self, callback: Callable[[str, str, str, str], None] | None
    ) -> None:
        self._on_receive_real_condition = callback

    def _receive_real_condition(
        self, code: str, event_type: str, cond_name: str, cond_index: str
    ) -> None:
        if self._on_receive_real_condition is not None:
            self._on_receive_real_condition(
                normalize_stock_code(code),
                str(event_type).strip().upper(),
                fix_kiwoom_text(str(cond_name)),
                str(cond_index).strip(),
            )

    def send_condition_stop(self, screen_no: str, cond_name: str, cond_index: int) -> None:
        self.dynamicCall(
            "SendConditionStop(QString, QString, int)",
            screen_no,
            cond_name,
            cond_index,
        )

    def send_condition(
        self, screen_no: str, cond_name: str, cond_index: int, search: int, block: bool = True
    ) -> int:
        if block and not self._events_wired:
            raise RuntimeError(
                "Condition search needs COM events. "
                "Run register_kiwoom_ocx_admin.bat as Administrator."
            )
        self._condition_codes = []
        ret = int(
            self.dynamicCall(
                "SendCondition(QString, QString, int, int)",
                screen_no,
                cond_name,
                cond_index,
                search,
            )
        )
        if block and ret == 1:
            self._condition_loop = QEventLoop()
            self._condition_loop.exec_()
        return ret

    def _receive_tr_condition(
        self, screen_no: str, codes: str, cond_name: str, cond_index: int, next_: int
    ) -> None:
        if codes:
            self._condition_codes.extend(parse_condition_code_list(codes))
        if next_ == 0 and self._condition_loop is not None and self._condition_loop.isRunning():
            self._condition_loop.exit()

    @property
    def condition_codes(self) -> list[str]:
        return list(self._condition_codes)
