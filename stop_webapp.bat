@echo off
REM ============================================================================
REM Emergency stop: full cleanup, no "press a key", no leftovers.
REM ============================================================================
setlocal EnableExtensions
cd /d "%~dp0"
set "CLEANUP=%~dp0scripts\cleanup_webapp_orphans.ps1"

echo [stop_webapp] Full cleanup...
if exist "%CLEANUP%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%CLEANUP%"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.ExecutablePath -like '*\QUOTEX\.venv\Scripts\python*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.CommandLine -like '*quotex_hub_edge*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; if (Test-Path 'runtime\main.lock') { Remove-Item 'runtime\main.lock' -Force -EA SilentlyContinue }"
)
echo [stop_webapp] Done. No pause — window can close.
exit /b 0
