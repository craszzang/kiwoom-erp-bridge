@echo off
chcp 65001 >nul
title GitHub 원클릭 설정
echo.
echo 저장소 이름: kiwoom-erp-bridge
echo 브라우저가 열리면 GitHub 로그인 1회만 하세요.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\github_oneclick.ps1"
echo.
pause
