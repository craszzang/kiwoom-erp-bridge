@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 키움 BRM 완전자동
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

if not exist "%PY%" (
    echo [자동] Python 환경 설치 중...
    call "%KK_ROOT%setup_env.bat"
)

if not exist "%PY%" (
    echo ERROR: setup_env 실패
    exit /b 1
)

if not exist "%KK_ROOT%config.yaml" (
    if exist "%KK_ROOT%config.automation.yaml" (
        copy /Y "%KK_ROOT%config.automation.yaml" "%KK_ROOT%config.yaml" >nul
        echo config.yaml 생성 (완전자동 프리셋)
    )
)

echo.
echo ========================================
echo  BRM 완전자동 (손대지 않음)
echo  로그: logs\auto_*.log , logs\brm_paper_*.csv
echo ========================================
echo.

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "READY=%LOCALAPPDATA%\kiwoom-trader\kiwoom_ready.flag"
if not exist "%READY%" echo ok>"%READY%"

cd /d "C:\OpenAPI"
"%PY%" -X utf8 "%KK_ROOT%auto_trader\excel_main.py" --auto
exit /b %ERRORLEVEL%
