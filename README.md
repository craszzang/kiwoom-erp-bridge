# Ű�� OpenAPI �ڵ��Ÿ�

Ű������ OpenAPI(COM) + Python 32��Ʈ + PyQt5 ��� �ڵ��Ÿ� ���̷����Դϴ�.

## ���� ����

| ��� | ���� |
|------|------|
| `OpenAPI/` | OpenAPI ���������̵� �Ϻ� (���� ���� ������ `C:\OpenAPI`) |
| `KOAStudioSA_ATS_ver 2.34/` | KOA Studio ��� �ȳ� (exe/dll�� OpenAPI ������ ���� �ʿ�) |
| `auto_trader/` | �ڵ��Ÿ� �ҽ� |
| `scripts/test_connection.py` | �α��Ρ��ü� ��ȸ �׽�Ʈ |
| `config.yaml` | ���� ���� (setup �� example���� ����) |

## ���� �غ� (����ڰ� ���� �ؾ� �ϴ� ��)

1. **Ű������ ����** + **Open API+ ��� ��û**  
   [Ű�� Open API+ �ٿ�ε�](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)  
   �� ��ġ �� �⺻ ��� `C:\OpenAPI` (�� PC���� �̹� ��ġ��)

2. **�������� ����** (����)  
   Ű�� Ȩ���������� �������� ��û ��, �α��� �� �������� ����

3. **32��Ʈ Python**  
   Ű�� OpenAPI�� **64��Ʈ ������**. ���� PC�� Python 3.12/3.14�� 64��Ʈ�� **���� ��� �Ұ�**.

4. **����������/��������**  
   `CommConnect()` �α��� â���� ���� ����

## ���� ����

```bat
setup_env.bat    :: 32��Ʈ Python + ��Ű�� ��ġ
run.bat test     :: �α��Ρ��ü��� �׽�Ʈ (�ֹ� ����)
run.bat          :: �ڵ��Ÿ� ����
```

`config.yaml`���� `account_no`, `watch_codes`, ���� �Ķ���͸� �����ϼ���.

## ���� (�⺻)

`SimpleMomentumStrategy` ? ���ÿ�:

- `watch_codes` �Ǵ� HTS **���ǰ˻�** ���� ����
- ���ذ� ��� `buy_drop_pct`% �϶� �� ���尡 �ż�
- �ż��� ��� `sell_rise_pct`% ��� �� ���尡 �ŵ�

���� ��� �� �ݵ�� �������ڷ� �����ϰ�, `strategy.py`�� ���� ������ �°� �����ϼ���.

## ���ǻ���

- OpenAPI �Լ�/�̺�Ʈ�� **���� ������**������ ȣ�� (��Ƽ������ �����)
- ���¹�ȣ�� **10�ڸ�** ��ü �Է�
- ȭ���ȣ�� 200�� �ѵ�, ���� ��ȣ�� ���� TR ��û ����
- `use_mock: true`�� �ΰ� �������� �α������� ���� �׽�Ʈ

## KOA Studio (����)

`KOAStudioSA.exe`, `KOALoader.dll`�� `C:\OpenAPI`�� ���� �� �����ϸ� TR/�ǽð� API�� GUI�� �׽�Ʈ�� �� �ֽ��ϴ�. (���� �������� �ȳ����� ����)
