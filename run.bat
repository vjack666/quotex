@echo off
REM ============================================================
REM  UNICO launcher: activa el servidor (app.py) y abre el hub.
REM  El bot se enciende desde el hub (boton "Iniciar").
REM  Reutiliza start_webapp.bat (cleanup automatico de huérfanos,
REM  abre el dashboard, soportado por el watchdog).
REM ============================================================
cd /d "%~dp0"
if not exist "start_webapp.bat" (
    echo [ERROR] Falta start_webapp.bat en %~dp0
    pause
    exit /b 1
)
call "%~dp0start_webapp.bat"
