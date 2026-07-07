@echo off

chcp 65001 >nul

setlocal EnableExtensions

title 자율 모의매매 루프 (무한)

call "%~dp0_paths.bat"

cd /d "%KK_ROOT%"



if not exist "%PY%" (

    echo [자율] Python 환경 설치 중...

    call "%KK_ROOT%setup_env.bat"

)



if not exist "%PY%" (

    echo ERROR: setup_env 실패

    exit /b 1

)



if not exist "%KK_ROOT%config.yaml" (

    if exist "%KK_ROOT%config.automation.yaml" (

        copy /Y "%KK_ROOT%config.automation.yaml" "%KK_ROOT%config.yaml" >nul

    )

)



set "STOP=%LOCALAPPDATA%\kiwoom-trader\autonomous_stop.flag"

if exist "%STOP%" del /F /Q "%STOP%"



echo.

echo ========================================
echo  자율 모의매매 — 무한 루프
echo  평일 08:45~15:25 캐치 당일매매 모의 + 자동개선 + Telegram
echo  시작 전 GitHub 최신 코드 동기화
echo  중지: 자율모의-중지.bat
echo ========================================
echo.

echo [자율] GitHub 동기화...
"%PY%" -X utf8 "%KK_ROOT%scripts\host_git_pull.py" 2>nul

set "PYTHONUTF8=1"

set "PYTHONIOENCODING=utf-8"

"%PY%" -X utf8 "%KK_ROOT%auto_trader\autonomous_daemon.py"

exit /b %ERRORLEVEL%

