@echo off
chcp 65001 >nul
echo Requesting Administrator to register Kiwoom OCX...
echo.

if not exist "C:\OpenAPI\khopenapi.ocx" (
    echo ERROR: C:\OpenAPI\khopenapi.ocx not found.
    pause
    exit /b 1
)

call "%~dp0fix_kiwoom_registry.bat"
exit /b %ERRORLEVEL%
