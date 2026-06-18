@echo off
chcp 65001 >nul
setlocal
call "%~dp0_paths.bat"
cd /d "%KK_ROOT%"
"%PY%" scripts\make_client_zip.py
echo.
echo 생성: %KK_ROOT%고객용 파일.zip
pause
