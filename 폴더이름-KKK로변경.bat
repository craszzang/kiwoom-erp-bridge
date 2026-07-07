@echo off
chcp 65001 >nul
set "TARGET=%~dp0"
set "PARENT=%~dp0.."
cd /d "%PARENT%"
if exist "KKK" (
  echo 이미 KKK 폴더가 있습니다.
  pause
  exit /b 1
)
if not exist "KK" (
  echo KK 폴더를 찾을 수 없습니다.
  pause
  exit /b 1
)
ren "KK" "KKK"
if errorlevel 1 (
  echo 이름 변경 실패 — Cursor를 완전히 종료한 뒤 다시 실행하세요.
  pause
  exit /b 1
)
echo 완료: KK -^> KKK
echo Cursor에서 새 경로를 열어주세요:
echo   %PARENT%KKK
pause
