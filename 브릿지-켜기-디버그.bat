@echo off
chcp 65001 >nul
title 키움 브릿지 (디버그)
echo.
echo [디버그] 이 창에 오류가 남습니다.
echo.
call "%~dp0브릿지-켜기.bat"
echo.
echo === 종료 코드: %ERRORLEVEL% ===
pause
