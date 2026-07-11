@echo off
REM ============================================================
REM  Panel STRAT-F — escaneo en vivo (solo lectura) + panel
REM  No opera. Descarga velas de ~14 pares y muestra el panel
REM  de aceptadas/rechazadas con la razon de cada rechazo.
REM ============================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno .venv
    pause
    exit /b 1
)
echo Escaneando pares en vivo (solo lectura) y grabando en el diario...
call .venv\Scripts\python.exe progress\diag_strat_f_live.py --journal > progress\diag_strat_f_filters.log 2>&1
if errorlevel 1 (
    echo [AVISO] El escaneo no termino (puede ser la demo). Se usa el ultimo log si existe.
)
echo.
echo Abriendo panel STRAT-F...
call .venv\Scripts\python.exe main.py --hub-readonly --once
echo.
pause
