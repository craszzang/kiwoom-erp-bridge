@echo off
chcp 65001 >nul
setlocal
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

if not exist "%PY%" (
    echo Installing Python environment...
    call "%KK_ROOT%setup_env.bat"
)

echo Installing bridge dependencies...
"%PY%" -m pip install -q requests websockets

echo.
echo ========================================
echo  키움 브릿지 서버 (호스트 PC)
echo  - 키움 OpenAPI는 이 PC에서만 동작
echo  - 고객 PC는 재고실적_집계-원격.bat 사용
echo ========================================
echo.

set "PYTHONUTF8=1"
cd /d "%KIWOOM_API%"
"%PY%" -X utf8 "%KK_ROOT%auto_trader\bridge_host_main.py"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" pause
exit /b %ERR%
