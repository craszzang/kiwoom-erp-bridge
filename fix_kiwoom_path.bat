@echo off
chcp 65001 >nul
setlocal
echo Kiwoom OpenAPI path fix...
echo.

taskkill /IM opversionup.exe /F >nul 2>&1
taskkill /IM opstarter.exe /F >nul 2>&1
taskkill /IM KHOpenAPI.exe /F >nul 2>&1

set "BAD=%~dp0OpenAPI"
set "BAK=%~dp0OpenAPI_backup"

if exist "%BAD%" (
    if exist "%BAK%" (
        echo Already renamed: OpenAPI_backup exists.
    ) else (
        ren "%BAD%" "OpenAPI_backup"
        if exist "%BAK%" (
            echo OK: KK\OpenAPI -^> OpenAPI_backup
        ) else (
            echo WARN: rename failed. Close Kiwoom/Excel app and retry.
        )
    )
) else (
    echo OK: KK\OpenAPI folder not found.
)

echo.
echo Real Kiwoom API path: C:\OpenAPI
if not exist "C:\OpenAPI\khopenapi.ocx" (
    echo ERROR: Install Kiwoom OpenAPI+ to C:\OpenAPI first.
    pause
    exit /b 1
)

echo.
echo Fixing OCX registry (Administrator UAC)...
call "C:\OpenAPI\fix_kiwoom_registry.bat"
exit /b %ERRORLEVEL%
