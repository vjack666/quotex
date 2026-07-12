@echo off
REM Launcher QUOTEX bot - doble clic para correr en DEMO (PRACTICE).
REM Usa el venv local. No cierra la ventana para poder leer los logs.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: no existe .venv. Crear con: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
echo ============================================
echo  CONSOLIDATION BOT - QUOTEX (DEMO / PRACTICE)
echo  Estrategia: STRAT-F (Wyckoff+Fractal) - solo lectura de velas cerradas
echo  Dashboard HUB: se imprime al arrancar (puerto variable)
echo ============================================
.venv\Scripts\python.exe main.py
echo.
echo [bot detenido] Pulsa una tecla para cerrar.
pause
