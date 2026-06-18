@echo off

chcp 65001 >nul

title ERP 원격 UI (디버그)

echo 검은 창이 바로 닫히면 이 파일로 실행하세요.

echo 오류 메시지가 이 창에 남습니다.

echo.

call "%~dp0재고실적_집계-원격.bat"

echo.

echo === 종료 코드: %ERRORLEVEL% ===

echo 로그: %~dp0remote_launch.log

pause

