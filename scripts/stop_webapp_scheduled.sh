#!/usr/bin/env bash
# Apagado programado de la QUOTEX Web App al terminar la ventana de 1 hora.
# Solo toca procesos de ESTE proyecto (python de .venv de QUOTEX, app.py/main.py
# bajo C:\Users\v_jac\Desktop\QUOTEX y el hub Edge con perfil quotex_hub_edge).
cd "$(dirname "$0")/.." || exit 1
TS="$(date '+%Y-%m-%d %H:%M:%S')"
cmd //c "stop_webapp.bat" > /dev/null 2>&1
sleep 3
LEFT="$(powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -like '*Desktop\\QUOTEX*' -and (\$_.CommandLine -like '*app.py*' -or \$_.CommandLine -like '*main.py*') } | Measure-Object).Count" 2>/dev/null | tr -d '\r\n ')"
echo "$TS STOP programado ejecutado; procesos QUOTEX restantes=$LEFT" >> runtime/webapp_watchdog.log
echo "[QUOTEX] $TS servidor detenido por fin de ventana de 1h. Procesos restantes: $LEFT"
