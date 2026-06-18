@echo off
REM Common paths (quoted for username with & character)
set "KK_ROOT=%~dp0"
for %%I in ("%LOCALAPPDATA%") do set "LOCAL_SHORT=%%~sI"
set "PY=%LOCAL_SHORT%\kiwoom-trader\.venv32\Scripts\python.exe"
set "QT_BASE=%LOCAL_SHORT%\kiwoom-trader\.venv32\Lib\site-packages\PyQt5\Qt5"
set "QT_QPA_PLATFORM_PLUGIN_PATH=%QT_BASE%\plugins\platforms"
set "QT_PLUGIN_PATH=%QT_BASE%\plugins"
set "PATH=%QT_BASE%\bin;%PATH%"
set "KIWOOM_API=C:\OpenAPI"
set "PATH=%KIWOOM_API%;%PATH%"
