@echo off
chcp 65001 >nul
setlocal EnableExtensions
title GitHub 동기화 후 자율 모의매매 시작

call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"

echo GitHub에서 최신 코드 받는 중...
if exist "%PY%" (
    "%PY%" -X utf8 "%KK_ROOT%scripts\host_git_pull.py"
) else (
    git pull --ff-only origin main
)

echo.
call "%~dp0자율모의.bat"
exit /b %ERRORLEVEL%
