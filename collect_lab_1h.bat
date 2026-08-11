@echo off
REM ============================================================================
REM collect_lab_1h.bat - Recolector de 1h para el laboratorio (EXP-039 / T4-B1)
REM
REM 1) Arranca el bot en PRACTICE + hub (ventana aparte via start_webapp.bat).
REM 2) Espera TIMEOUT_SECS de captura en vivo (1 hora por defecto).
REM 3) Detiene el servidor (stop_webapp.bat).
REM 4) Corre el analizador EXP-039 sobre el log REAL de la corrida.
REM
REM REQUISITO: QUOTEX_DEMO_SSID debe estar en .env, sino el login falla 403.
REM EDITABLE: cambia TIMEOUT_SECS para otra duracion de captura.
REM ============================================================================
setlocal EnableExtensions
title QUOTEX Lab - recolector 1h
cd /d "%~dp0"

set "TIMEOUT_SECS=3600"
set "PY=%~dp0.venv\Scripts\python.exe"
set "LOG=data\logs\runtime\consolidation_bot.log"
set "OUT=src\strategy_lab\results\exp039_live_validation.json"

echo ============================================================
echo  QUOTEX Lab - recolector de muestras (1 hora)
echo  - Bot PRACTICE + hub en ventana aparte
echo  - Captura %TIMEOUT_SECS%s y luego analisis EXP-039
echo  - Log: %LOG%
echo ============================================================
echo.

echo [LAB] Arrancando servidor (bot PRACTICE + hub)...
start "" cmd /c start_webapp.bat

echo [LAB] Esperando %TIMEOUT_SECS% segundos de captura en vivo...
timeout /t %TIMEOUT_SECS% /nobreak

echo [LAB] Tiempo cumplido. Deteniendo servidor...
call stop_webapp.bat

echo [LAB] Analizando captura con EXP-039...
"%PY%" src\strategy_lab\scripts\exp039_analyze.py --log "%LOG%" --out "%OUT%"

echo.
echo [LAB] Listo. Veredicto en: %OUT%
pause
