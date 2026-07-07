@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv32\Scripts\python.exe (
    set PY=.venv32\Scripts\python.exe
) else (
    set PY=python
)
echo BRM v3 모의 테스트 (키움 호스트 PC에서 실행)
echo  - 장중 09:00~11:00 에 체크
echo  - 상단 "BRM 모의" 체크 후 조건식 종목 관찰
echo  - 로그: logs\brm_paper_YYYYMMDD.csv
echo.
"%PY%" -m pytest tests\test_brm_engine.py -q
if errorlevel 1 pause & exit /b 1
echo.
echo 지표 단위테스트 OK. 실시간은 재고실적_집계.bat 또는 브릿지-켜기 후 UI에서 BRM 모의 ON
"%PY%" -m auto_trader.excel_main
pause
