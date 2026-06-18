# -*- coding: utf-8 -*-
"""�α��Ρ����� ��ȸ �׽�Ʈ (�ֹ� ����)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt5.QtWidgets import QApplication

from auto_trader.config import load_config
from auto_trader.kiwoom_api import KiwoomAPI


def main() -> int:
    config = load_config()
    app = QApplication.instance() or QApplication(sys.argv)
    api = KiwoomAPI()

    if config.use_mock:
        acc = config.mock_account_no or config.account_no
        print("[ĳġ����] �α���: �������� ���� + ĳġ���� ����")
        if acc:
            print(f"  ���� ����: {acc} (ȭ��ǥ�� 9824-0694)")

    print("Ű�� �α��� â�� �����ϴ�...")
    err = api.comm_connect()
    if err != 0:
        print(f"�α��� ����: err_code={err}")
        return 1

    server = api.get_login_info("GetServerGubun")
    is_mock = server == "1"
    print("�α��� ����")
    print(f"  ID: {api.get_login_info('USER_ID')}")
    print(f"  �̸�: {api.get_login_info('USER_NAME')}")
    print(f"  ����: {'��������' if is_mock else '�Ǽ���'} (GetServerGubun={server})")
    accounts = api.get_accounts()
    print(f"  ����({len(accounts)}): {', '.join(accounts)}")

    if config.mock_account_no:
        print(f"  config ����: {config.mock_account_no}")

    api.set_input_value("�����ڵ�", "005930")
    api.comm_rq_data("�����׽�Ʈ", "opt10001", 0, "9999")
    name = api.get_comm_data("opt10001", "�����׽�Ʈ", 0, "�����")
    price = api.get_comm_data("opt10001", "�����׽�Ʈ", 0, "���簡")
    print(f"  �ü��׽�Ʈ: {name} ���簡 {price}")
    print("���� �׽�Ʈ �Ϸ�")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
