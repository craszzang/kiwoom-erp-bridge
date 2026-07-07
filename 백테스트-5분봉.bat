@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 5분봉 백테스트
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

if not exist "%PY%" (
    echo Python 환경 설치 중...
    call "%KK_ROOT%setup_env.bat"
)

if not exist "%PY%" (
    echo ERROR: .venv32 없음 — setup_env.bat 실행
    pause
    exit /b 1
)

echo.
echo ========================================
echo  5분봉 백테스트
echo  기본: 샘플 데이터 (키움 로그인 불필요)
echo  설정: backtest_5m\config.backtest.yaml
echo ========================================
echo.

set "PYTHONUTF8=1"
"%PY%" -X utf8 "%KK_ROOT%tests\test_backtest_5m.py"
if errorlevel 1 (
    echo 단위검증 실패
    pause
    exit /b 1
)

"%PY%" -X utf8 "%KK_ROOT%backtest_5m\run_backtest.py" %*
set "ERR=%ERRORLEVEL%"
echo.
if not "%ERR%"=="0" pause
exit /b %ERR%
