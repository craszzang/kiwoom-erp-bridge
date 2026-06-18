"""Create customer delivery ZIP in KK folder."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = ROOT / "고객용 파일.zip"
STAGE = ROOT / "고객용 파일"
REPO_FILE = ROOT / "github_repo.txt"
DEFAULT_REPO = "kiwoom-erp-bridge"


def _github_repo_line() -> str:
    if REPO_FILE.is_file():
        line = REPO_FILE.read_text(encoding="utf-8").strip()
        if line:
            return line
    return f"YOUR_GITHUB_USER/{DEFAULT_REPO}"

CLIENT_CONFIG = """use_mock: true
mock_mode: catch
account_no: ''
screen_no: '0101'
real_screen_no: '0102'
tr_screen_no: '0103'
watch_mode: market
watch_codes:
- 005930
condition_name: ''
condition_index: 0
max_positions: 3
order_qty: 1
log_level: INFO
filters:
  min_sell_balance_pct: 50.0
  min_execution_strength: 70.0
  filter_pass_only: true
bridge:
  role: client
  host: '100.83.138.124'
  port: 8765
  http_port: 8766
  token: ''
  auto_sync: false
update:
  source: github
  github_repo: '{_github_repo_line()}'
  github_branch: main
  github_mode: manifest
  github_asset: client.zip
""".replace("{_github_repo_line()}", _github_repo_line())

GUIDE = """[ ERP 원격 UI - 고객 PC 설치 안내 ]

1) 이 ZIP을 풀기 (예: C:\\ERP)

2) 최초 1회: setup_remote.bat 더블클릭
   - Python + PyQt5 자동 설치 (5~10분)
   - "설치 완료!" 메시지가 나와야 함
   ※ setup_env.bat 은 사용하지 마세요 (호스트용)

3) 시연 당일: 재고실적_집계-원격.bat 실행 → F5

4) 검은 창이 바로 닫히면:
   - 재고실적_집계-원격-디버그.bat 실행 (오류 메시지 확인)
   - 또는 remote_launch.log 파일 열기

5) 연결 안 되면 (고객 PC cmd):
   ping 192.168.0.11
   ※ 같은 Wi-Fi 여야 함. 호스트에서 브릿지-방화벽열기.bat (관리자) 1회

호스트 IP가 바뀌면 config.yaml 의 bridge.host 수정
"""

COPY_FILES = (
    "setup_remote.bat",
    "setup_remote.ps1",
    "_paths_remote.bat",
    "requirements-remote.txt",
    "재고실적_집계-원격.bat",
    "재고실적_집계-원격-디버그.bat",
)


def _ignore_pycache(dir_path: str, names: list[str]) -> set[str]:
    return {n for n in names if n == "__pycache__"}


def main() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "client"
        stage.mkdir()
        shutil.copytree(ROOT / "auto_trader", stage / "auto_trader", ignore=_ignore_pycache)
        for name in COPY_FILES:
            shutil.copy2(ROOT / name, stage / name)
        (stage / "config.yaml").write_text(CLIENT_CONFIG, encoding="utf-8")
        (stage / "고객설치안내.txt").write_text(GUIDE, encoding="utf-8")

        with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(stage).as_posix())

        count = sum(1 for _ in stage.rglob("*") if _.is_file())

    print(f"created: {ZIP_PATH}")
    print(f"size: {ZIP_PATH.stat().st_size:,} bytes")
    print(f"files: {count}")


if __name__ == "__main__":
    main()
