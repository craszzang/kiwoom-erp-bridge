@echo off

chcp 65001 >nul

echo ========================================

echo  브릿지 방화벽 허용 (호스트 PC, 관리자)

echo  TCP 8765 (WS), 8766 (HTTP)

echo ========================================

echo.



netsh advfirewall firewall add rule name="Kiwoom Bridge WS" dir=in action=allow protocol=TCP localport=8765

netsh advfirewall firewall add rule name="Kiwoom Bridge HTTP" dir=in action=allow protocol=TCP localport=8766



echo.

echo 완료. 고객 PC에서 ping 호스트IP 후 원격 UI 실행하세요.

pause

