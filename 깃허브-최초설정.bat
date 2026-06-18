@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo  GitHub 최초 1회 설정 (호스트 PC)
echo ========================================
echo.
echo 1) github.com 에서 새 PUBLIC 저장소 만들기
echo 2) 아래에서 GitHub 사용자명/저장소명 입력
echo.

set /p REPO=GitHub 저장소 (예: myuser/kk-trader): 
if "%REPO%"=="" (
    echo 취소
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\github_push.ps1" -Repo "%REPO%"
pause
