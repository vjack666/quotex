@echo off
REM Feature 41 (R1): launcher del Hub Operacional del Edificio.
REM Arranca app.py (servidor del hub) y abre el navegador en la URL del hub.
cd /d "%~dp0\.."
if not exist .env (
    echo ADVERTENCIA: no se encontro .env — el bot no podra conectar al broker.
)
start "" python app.py
timeout /t 3 >nul
start "" http://127.0.0.1:5000
exit /b 0
