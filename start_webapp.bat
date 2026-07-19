@echo off
REM ============================================================================
REM ONE process: this console runs app.py.
REM On ANY exit (Ctrl+C, X, crash, code != 0): full cleanup, NO "press a key".
REM Window closes; no python / Edge hub zombies left.
REM ============================================================================
setlocal EnableExtensions
title QUOTEX Web App
cd /d "%~dp0"

set "PORT=8080"
set "PY=%~dp0.venv\Scripts\python.exe"
set "URL=http://127.0.0.1:%PORT%/"
set "HUB_NO_OPEN="
set "CLEANUP=%~dp0scripts\cleanup_webapp_orphans.ps1"

if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  call :full_cleanup
  exit /b 1
)
if not exist "%~dp0app.py" (
  echo [ERROR] Missing app.py
  call :full_cleanup
  exit /b 1
)

REM Case A: already healthy - open hub once and exit (no second server)
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/api/bot/status' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% equ 0 (
  echo [OK] Server already running.
  echo [OK] Opening hub dashboard...
  if exist "%~dp0scripts\open_hub_when_ready.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\open_hub_when_ready.ps1" -Port %PORT% -MaxAttempts 3
  )
  exit /b 0
)

REM Case B: cold start
if exist "%CLEANUP%" (
  echo [..] Cleaning previous orphans...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%CLEANUP%"
)

echo.
echo ============================================================
echo   QUOTEX Web App - single process
echo   %URL%
echo.
echo   Hub opens automatically
echo   Close window or Ctrl+C = full stop + cleanup (no pause)
echo ============================================================
echo.

"%PY%" app.py --port %PORT%
set "RC=%ERRORLEVEL%"

echo.
echo [QUOTEX] Server exited code %RC% — cleaning up...
call :full_cleanup
echo [QUOTEX] Cleanup done. Nothing left pending.
exit /b %RC%

:full_cleanup
if exist "%CLEANUP%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%CLEANUP%"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.ExecutablePath -like '*\QUOTEX\.venv\Scripts\python*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { $_.CommandLine -like '*quotex_hub_edge*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; if (Test-Path 'runtime\main.lock') { Remove-Item 'runtime\main.lock' -Force -EA SilentlyContinue }; if (Test-Path 'runtime\webapp.pid') { Remove-Item 'runtime\webapp.pid' -Force -EA SilentlyContinue }"
)
exit /b 0
