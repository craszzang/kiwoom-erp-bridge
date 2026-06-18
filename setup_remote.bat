@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
echo.
echo ========================================
echo  ERP 원격 UI - 최초 1회 설치
echo  (키움 불필요, Python+PyQt5만 설치)
echo ========================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%setup_remote.ps1"
if errorlevel 1 (
    echo.
    echo [설치 실패] 위 빨간 메시지를 확인하세요.
    pause
    exit /b 1
)
echo.
pause
