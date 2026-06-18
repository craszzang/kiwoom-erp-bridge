@echo off

REM Remote client paths (no Kiwoom / 64-bit venv)

set "KK_ROOT=%~dp0"

set "PY=%LOCALAPPDATA%\kiwoom-trader\.venv-remote\Scripts\python.exe"

set "QT_BASE=%LOCALAPPDATA%\kiwoom-trader\.venv-remote\Lib\site-packages\PyQt5\Qt5"

if exist "%QT_BASE%\plugins\platforms" (

    set "QT_QPA_PLATFORM_PLUGIN_PATH=%QT_BASE%\plugins\platforms"

    set "QT_PLUGIN_PATH=%QT_BASE%\plugins"

    set "PATH=%QT_BASE%\bin;%PATH%"

)

