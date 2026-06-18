@echo off
chcp 65001 >nul
echo Register Kiwoom OpenAPI OCX (32-bit)...
echo.

if not exist "C:\OpenAPI\khopenapi.ocx" (
    echo ERROR: C:\OpenAPI\khopenapi.ocx not found.
    echo Install Kiwoom OpenAPI+ from kiwoom.com first.
    pause
    exit /b 1
)

taskkill /IM opversionup.exe /F >nul 2>&1
taskkill /IM opstarter.exe /F >nul 2>&1

%SystemRoot%\SysWOW64\regsvr32 /s "C:\OpenAPI\khopenapi.ocx"
if errorlevel 1 (
    echo.
    echo FAILED. Right-click this file -^> Run as administrator
    pause
    exit /b 1
)

echo OK: khopenapi.ocx registered.
echo.
pause
