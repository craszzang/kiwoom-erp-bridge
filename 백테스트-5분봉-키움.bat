@echo off
chcp 65001 >nul
call "%~dp0_paths.bat"
cd /d "C:\OpenAPI"
echo 키움 로그인 후 실제 5분봉으로 백테스트합니다...
"%PY%" -X utf8 "%KK_ROOT%backtest_5m\run_backtest.py" --source kiwoom %*
pause
