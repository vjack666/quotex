@echo off
setlocal
set URL=http://127.0.0.1:8080/
set LOG=%~dp0runtime\webapp_watchdog.log
set CHECK=%~dp0scripts\check_webapp_health.ps1
if not exist "%CHECK%" (
  echo [WATCHDOG] Missing %CHECK% > "%LOG%"
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%CHECK%" >> "%LOG%" 2>&1
exit /b %ERRORLEVEL%
