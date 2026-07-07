@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 키움 브릿지 서버
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

echo.
echo ========================================
echo  키움 브릿지 서버 (호스트 PC)
echo ========================================
echo  폴더: %KK_ROOT%
echo  Python: %PY%
echo.

if not exist "%PY%" (
    echo [오류] Python 32bit 환경이 없습니다.
    echo setup_env.bat 을 먼저 실행하세요.
    echo.
    pause
    exit /b 1
)

if not exist "C:\OpenAPI\khopenapi.ocx" (
    echo [오류] C:\OpenAPI\khopenapi.ocx 가 없습니다.
    echo 키움 OpenAPI+ 를 설치하세요.
    echo.
    pause
    exit /b 1
)

echo bridge 패키지 확인 중...
"%PY%" -m pip install -q requests websockets 2>nul

echo 브릿지 시작 중... (키움 로그인 창이 곧 뜹니다)
echo.

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "C:\OpenAPI"
"%PY%" -X utf8 "%KK_ROOT%auto_trader\bridge_host_main.py"
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
    echo.
    echo [실행 실패] 종료 코드 %ERR%
    pause
    exit /b %ERR%
)

exit /b 0
