@echo off
chcp 65001 >nul
setlocal
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

if not exist "%PY%" (
    echo Installing Python environment...
    call "%KK_ROOT%setup_env.bat"
)

if not exist "%PY%" (
    echo ERROR: setup failed. Run setup_env.bat manually.
    pause
    exit /b 1
)

if not exist "%QT_QPA_PLATFORM_PLUGIN_PATH%\qwindows.dll" (
    echo ERROR: PyQt5 plugin missing. Run setup_env.bat again.
    pause
    exit /b 1
)

set "PYTHONUTF8=1"
set "READY=%LOCALAPPDATA%\kiwoom-trader\kiwoom_ready.flag"

if not exist "%READY%" (
    echo.
    echo [FIRST TIME] Run Ű��_�ѹ���_����.bat once before this program.
    echo.
    choice /C YN /M "Open Ű��_�ѹ���_����.bat now"
    if not errorlevel 2 (
        call "%~dp0Ű��_�ѹ���_����.bat"
    )
)

echo Starting Excel UI...
echo Press F5 in the window to connect ERP after it opens.
cd /d "%KIWOOM_API%"
"%PY%" -X utf8 "%KK_ROOT%auto_trader\excel_main.py"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo ERROR: exit code %ERR%
    pause
)
