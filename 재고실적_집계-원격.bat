@echo off

chcp 65001 >nul

setlocal EnableExtensions

call "%~dp0_paths_remote.bat"

cd /d "%KK_ROOT%"



set "LOG=%KK_ROOT%remote_launch.log"

echo.>>"%LOG%"

echo ===== %date% %time% =====>>"%LOG%"

echo KK_ROOT=%KK_ROOT%>>"%LOG%"

echo PY=%PY%>>"%LOG%"



if not exist "%PY%" (

    echo Python 환경이 없습니다. setup_remote.bat 을 먼저 실행하세요.

    echo Python 환경이 없습니다. setup_remote.bat 을 먼저 실행하세요.>>"%LOG%"

    echo.

    call "%KK_ROOT%setup_remote.bat"

    if not exist "%PY%" (

        echo 설치 실패. remote_launch.log 확인.

        echo 설치 실패>>"%LOG%"

        pause

        exit /b 1

    )

)



echo ERP 원격 UI 시작 중... (상태 창이 곧 뜹니다)

echo ERP 원격 UI 시작 중...>>"%LOG%"



set "PYTHONUTF8=1"

set "PYTHONIOENCODING=utf-8"

REM GUI 앱은 로그 리다이렉트 없이 실행 (팝업이 cmd 뒤에 숨는 문제 방지)

"%PY%" -X utf8 -u "%KK_ROOT%auto_trader\remote_main.py"

set "ERR=%ERRORLEVEL%"

echo exit code=%ERR%>>"%LOG%"



if not "%ERR%"=="0" (

    echo.

    echo [실행 실패] remote_launch.log 를 확인하세요:

    echo   %LOG%

    echo.

    if exist "%LOG%" type "%LOG%"

    echo.

    pause

    exit /b %ERR%

)



exit /b 0

