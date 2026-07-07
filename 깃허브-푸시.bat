@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  GitHub push (kiwoom-erp-bridge)
echo  Actions: CI tests + client.zip release
echo ========================================
echo.

git add .github .gitignore _paths.bat _paths_remote.bat setup_env.ps1 setup_env.bat
git add auto_trader backtest_5m scripts tests strategies data
git add config.yaml.example config.automation.yaml config.brm.example.yaml config.telegram.example.yaml
git add requirements-remote.txt setup_remote.bat setup_remote.ps1 sync
git add *.bat

git status
echo.
set /p MSG=커밋 메시지 (Enter=feat: autonomous daily trading + backtest): 
if "%MSG%"=="" set "MSG=feat: autonomous daily trading + backtest"
git commit -m "%MSG%"
if errorlevel 1 (
    echo 커밋할 변경 없음 또는 실패
    pause
    exit /b 1
)
git push origin main
echo.
echo push 완료. GitHub Actions가 테스트 및 client.zip 릴리스를 만듭니다.
echo 호스트 PC: 호스트-깃허브동기화-자율시작.bat 또는 자율모의.bat
pause
