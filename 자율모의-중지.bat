@echo off

chcp 65001 >nul

setlocal

set "STOP=%LOCALAPPDATA%\kiwoom-trader\autonomous_stop.flag"

echo stop>%STOP%

echo 자율 모의매매 중지 플래그 설정됨.

echo 실행 중인 자율모의.bat / 완전자동.bat 은 다음 루프에서 종료됩니다.

pause

