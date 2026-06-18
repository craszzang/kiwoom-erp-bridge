@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%setup_env.ps1"
echo.
pause
