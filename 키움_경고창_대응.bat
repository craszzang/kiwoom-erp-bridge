@echo off
chcp 65001 >nul
echo ========================================
echo  Kiwoom version warning - how to respond
echo  (Official Kiwoom OpenAPI guide)
echo ========================================
echo.
echo WRONG: Close the login window
echo RIGHT: Keep login window OPEN
echo.
echo Steps when opstarter WARNING appears:
echo.
echo  1. Keep Kiwoom login window + warning as they are
echo  2. Task Manager - end ONLY:
echo       - Python(32-bit)
echo       - Do NOT end NKStarter yet
echo  3. Click OK on the warning
echo  4. Wait until "initial file download" finishes
echo  5. Then login (mock investment checked)
echo.
echo ----------------------------------------
echo  Skip update loop (recommended now)
echo ----------------------------------------
echo.
echo OCX registry is OK. You do NOT need
echo kiwoom_reset_update.bat anymore.
echo.
echo  1. End Python + NKStarter in Task Manager
echo  2. Run: 재고실적_집계.bat
echo  3. Data - ERP remote link
echo  4. If warning: kill Python only, click OK
echo.
pause
