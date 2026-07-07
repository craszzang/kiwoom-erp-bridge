@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "TASK=KiwoomBRM_FullAuto"

echo ========================================
echo  완전자동 — 최초 1회 설정
echo  (이후 손댈 필요 없음)
echo ========================================
echo.

cd /d "%ROOT%"

echo [1/5] 키움 경로 정리...
if exist "%ROOT%fix_kiwoom_path.bat" call "%ROOT%fix_kiwoom_path.bat"

echo [2/5] Python 32bit 환경...
call "%ROOT%setup_env.bat"
if errorlevel 1 (
    echo setup_env 실패
    pause
    exit /b 1
)

echo [3/5] OCX 등록 (관리자 필요할 수 있음)...
if exist "%ROOT%register_kiwoom_ocx_admin.bat" (
    powershell -Command "Start-Process -FilePath '%ROOT%register_kiwoom_ocx_admin.bat' -Verb RunAs -Wait" 2>nul
    if errorlevel 1 call "%ROOT%register_kiwoom_ocx.bat"
)

echo [4/5] config.yaml (완전자동)...
if exist "%ROOT%config.automation.yaml" (
    copy /Y "%ROOT%config.automation.yaml" "%ROOT%config.yaml" >nul
)

set "READY=%LOCALAPPDATA%\kiwoom-trader\kiwoom_ready.flag"
echo ok>"%READY%"

echo [5/5] Windows 작업 스케줄 등록...
schtasks /Delete /TN "%TASK%" /F >nul 2>&1
schtasks /Create /TN "%TASK%" /TR "\"%ROOT%완전자동.bat\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 08:50 /RL HIGHEST /F
if errorlevel 1 (
    echo 스케줄 등록 실패 — 관리자로 다시 실행하세요.
    schtasks /Create /TN "%TASK%" /TR "\"%ROOT%완전자동.bat\"" /SC ONLOGON /RL HIGHEST /F
)

schtasks /Delete /TN "KiwoomBridgeAutoStart" /F >nul 2>&1
schtasks /Create /TN "KiwoomBridgeAutoStart" /TR "\"%ROOT%완전자동.bat\"" /SC ONLOGON /RL HIGHEST /F >nul 2>&1

echo.
echo ========================================
echo  설정 완료
echo.
echo  키움 HTS에서 딱 1번만:
echo    로그인 창 - 모의투자 - 캐치모의
echo    + 자동로그인 체크 저장
echo.
echo  이후: PC 켜면 / 평일 08:50 자동 실행
echo  종료: 11:05 자동 (BRM 모의)
echo  로그: %ROOT%logs\
echo ========================================
echo.
start "" "%ROOT%완전자동.bat"
