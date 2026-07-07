@echo off
chcp 65001 >nul
setlocal EnableExtensions
call "%~dp0_paths.bat"
cd /d "C:\OpenAPI"

if not exist "C:\OpenAPI\opstarter.exe" (
    echo ERROR: C:\OpenAPI\opstarter.exe not found
    pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq opstarter.exe" 2>nul | find /I "opstarter.exe" >nul
if errorlevel 1 start "" /B "C:\OpenAPI\opstarter.exe"

if not exist "%PY%" (
    echo Installing Python 32-bit...
    call "%KK_ROOT%setup_env.bat"
)

echo Starting Kiwoom login window...
start "Kiwoom Login" /WAIT "%PY%" -X utf8 "%KK_ROOT%auto_trader\kiwoom_login.py"
exit /b %ERRORLEVEL%
