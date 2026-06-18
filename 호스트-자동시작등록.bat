@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "TASK=KiwoomBridgeAutoStart"

echo ========================================
echo  브릿지 로그인 시 자동 실행 등록
echo  (PC 켜지면 브릿지-켜기.bat 실행)
echo ========================================
echo.

schtasks /Create /TN "%TASK%" /TR "\"%ROOT%브릿지-켜기.bat\"" /SC ONLOGON /RL HIGHEST /F
if errorlevel 1 (
    echo [실패] 관리자 권한으로 다시 실행해 보세요.
    pause
    exit /b 1
)

echo.
echo 등록 완료. 다음 로그인부터 브릿지가 자동 실행됩니다.
echo 전원: Windows 설정 - 전원 - 절전 '안 함' 권장
pause
