@echo off

chcp 65001 >nul

setlocal

set "ROOT=%~dp0"

set "TASK=KiwoomAutonomousMock"



echo ========================================

echo  자율 모의매매 — 최초 1회 설정

echo ========================================

echo.



cd /d "%ROOT%"



call "%ROOT%setup_env.bat"

if errorlevel 1 (

    echo setup_env 실패

    pause

    exit /b 1

)



if exist "%ROOT%config.automation.yaml" (

    copy /Y "%ROOT%config.automation.yaml" "%ROOT%config.yaml" >nul

)



if not exist "%ROOT%config.telegram.yaml" (

    if exist "%ROOT%config.telegram.example.yaml" (

        copy /Y "%ROOT%config.telegram.example.yaml" "%ROOT%config.telegram.yaml" >nul

        echo config.telegram.yaml 생성 — bot_token/chat_id 입력 필요

    )

)



set "READY=%LOCALAPPDATA%\kiwoom-trader\kiwoom_ready.flag"

echo ok>"%READY%"

set "STOP=%LOCALAPPDATA%\kiwoom-trader\autonomous_stop.flag"

if exist "%STOP%" del /F /Q "%STOP%"



schtasks /Delete /TN "%TASK%" /F >nul 2>&1

schtasks /Create /TN "%TASK%" /TR "\"%ROOT%자율모의.bat\"" /SC ONLOGON /RL HIGHEST /F

if errorlevel 1 (

    echo 스케줄 등록 실패 — 관리자로 다시 실행하세요.

)



echo.

echo  키움 HTS 1회: 캐치모의 + 자동로그인

echo  Telegram: config.telegram.yaml 에 토큰/채팅ID

echo  시작: 자율모의.bat  |  중지: 자율모의-중지.bat

echo.

start "" "%ROOT%자율모의.bat"

