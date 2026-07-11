@echo off
REM ============================================================
REM  Calibracion STRAT-F — lee el diario y sugiere ajustes
REM  de umbrales (no opera, solo analiza datos guardados).
REM  Requiere haber corrido run_strat_f_panel.bat al menos 1 vez.
REM ============================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno .venv
    pause
    exit /b 1
)
echo.
echo Reporte de calibracion STRAT-F (ultimos 90 dias):
echo.
call .venv\Scripts\python.exe -m src.calibration_report 90
echo.
pause
