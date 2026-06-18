@echo off
chcp 65001 >nul
setlocal
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

if not exist "%PY%" (
    echo [1? ???] Python ??? ??? ??...
    call "%KK_ROOT%setup_env.bat"
)

if not exist "%PY%" (
    echo setup_env.bat ???? ?? ??? ????????.
    pause
    exit /b 1
)

if /I "%~1"=="check" (
    cd /d "%KIWOOM_API%"
    "%PY%" -X utf8 "%KK_ROOT%scripts\check_kiwoom_env.py"
    goto :done
)

if /I "%~1"=="excel" (
    cd /d "%KIWOOM_API%"
    "%PY%" -X utf8 "%KK_ROOT%auto_trader\excel_main.py"
    goto :done
)

if /I "%~1"=="test" (
    cd /d "%KIWOOM_API%"
    "%PY%" -X utf8 "%KK_ROOT%scripts\test_connection.py"
    goto :done
)

if /I "%~1"=="mock" (
    if /I "%~2"=="register" (
        "%PY%" "%KK_ROOT%scripts\setup_mock_account.py" --register
    ) else if /I "%~2"=="login" (
        cd /d "%KIWOOM_API%"
        "%PY%" -X utf8 "%KK_ROOT%scripts\setup_mock_account.py" --login
    ) else (
        cd /d "%KIWOOM_API%"
        "%PY%" -X utf8 "%KK_ROOT%scripts\setup_mock_account.py"
    )
    goto :done
)

cd /d "%KIWOOM_API%"
"%PY%" -X utf8 "%KK_ROOT%auto_trader\main.py"

:done
pause
