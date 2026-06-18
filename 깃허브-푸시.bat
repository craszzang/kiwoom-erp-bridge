@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo GitHub에 코드 올리는 중...
git add auto_trader scripts requirements-remote.txt setup_remote.bat setup_remote.ps1 _paths_remote.bat "재고실적_집계-원격.bat" "재고실적_집계-원격-디버그.bat" sync .github
git status
echo.
set /p MSG=커밋 메시지 (Enter=update): 
if "%MSG%"=="" set "MSG=update"
git commit -m "%MSG%"
git push
echo.
echo push 완료. GitHub Actions가 client.zip 릴리스를 만듭니다.
pause
