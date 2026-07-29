@echo off
REM ============================================================================
REM SINGLE INSTANCE: this console runs main.py (BOT + dashboard HUB in ONE
REM process). main.py is the UNIQUE executor: levanta el bot DEMO y el HUB
REM integrado, y le pasa el bot al HUB para panel STRAT-F en vivo.
REM On ANY exit (Ctrl+C, X, crash, code != 0): full cleanup, NO "press a key".
REM Window closes; no python / Edge hub zombies left.
REM
REM Ruben 2026-07-26: main.py = unico ejecutor (bot+HUB unificados). El acceso
REM directo del escritorio lo levanta. Single-instance guard mata instancias
REM previas para quedar EXACTAMENTE UNA.
REM ============================================================================
setlocal EnableExtensions
title QUOTEX Web App
cd /d "%~dp0"

set "PORT=8080"
set "PY=%~dp0.venv\Scripts\python.exe"
set "URL=http://127.0.0.1:%PORT%/"
set "HUB_NO_OPEN="
REM Agente vivo STRAT-F: aprende de cada trade resuelto en tiempo real (Ruben 2026-07-24).
set "AGENT_LIVE=1"
set "CLEANUP=%~dp0scripts\cleanup_webapp_orphans.ps1"

if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  call :full_cleanup
  exit /b 1
)
if not exist "%~dp0main.py" (
  echo [ERROR] Missing main.py
  call :full_cleanup
  exit /b 1
)

REM --- SINGLE INSTANCE GUARD ------------------------------------------------
REM Garantizar EXACTAMENTE UNA instancia: matar cualquier instancia previa de
REM este proyecto (app.py + bot + uvicorn + Edge hub + otros .bat del acceso
REM directo) antes de arrancar. El acceso directo puede usarse varias veces;
REM el ultimo que arranca mata a los anteriores y queda uno solo.
if exist "%CLEANUP%" (
  echo [..] Single-instance guard: killing previous instances...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%CLEANUP%"
)
REM Kill-and-verify loop: asegurar EXACTAMENTE 0 instancias de app.py de este
REM proyecto antes de arrancar (evita bots duplicados por timing/race).
REM Tambien mata el Edge hub: si el hub revivia el server, aparecerian bots
REM duplicados. Se mata en bucle hasta 0 app.py.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$n=1; while($n -gt 0){ $p=Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object { ($_.CommandLine -like '*main.py*') -or ($_.CommandLine -like '*app.py*') -or ($_.CommandLine -like '*quotex_hub_edge*') }; $n=$p.Count; if($n -gt 0){ $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; Start-Sleep -Milliseconds 500 } }; Write-Host '[OK] 0 instancias previas (main.py/app.py/hub)'"
timeout /t 2 >nul

echo.
echo ============================================================
echo   QUOTEX Web App - single instance (bot + dashboard unificados via main.py)
echo   %URL%
echo.
echo   Hub opens automatically
echo   Close window or Ctrl+C = full stop + cleanup (no pause)
echo ============================================================
echo.

"%PY%" app.py
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
