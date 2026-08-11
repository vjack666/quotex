#!/usr/bin/env bash
# Vigilante ligero QUOTEX Web App (solo observa, NO reinicia, NO mata nada ajeno).
# Escribe una linea por chequeo en runtime/webapp_watchdog.log. Salida silenciosa
# (stdout vacio) salvo que el servidor este caido.
#
# OJO: filtrar SIEMPRE por Name -eq 'python.exe'. Un Where-Object solo por
# CommandLine cuenta tambien los bash/powershell del propio agente, porque el
# patron de busqueda aparece en su propia linea de comandos (falso positivo).
cd /c/Users/v_jac/Desktop/QUOTEX || exit 1
LOG="runtime/webapp_watchdog.log"
mkdir -p runtime
TS="$(date '+%Y-%m-%d %H:%M:%S')"
CODE="$(curl -s -o /dev/null -m 8 -w '%{http_code}' http://127.0.0.1:8080/ 2>/dev/null)"
NPROC="$(powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -like '*QUOTEX*' -and \$_.CommandLine -like '*app.py*' } | Measure-Object).Count" 2>/dev/null | tr -d '\r\n ')"
LOCK="$(cat runtime/main.lock 2>/dev/null | tr -d '\r\n ')"
DB="$(ls -t data/db/black_box_strat_*.db 2>/dev/null | head -1)"
LASTSCAN="-"
if [ -n "$DB" ]; then
  LASTSCAN="$(.venv/Scripts/python.exe -c "import sqlite3,sys,time
try:
    c=sqlite3.connect(sys.argv[1]); r=c.execute('SELECT MAX(ts) FROM scan_candidates').fetchone()[0]
    print('-' if r is None else '%.1fmin' % ((time.time()-float(r))/60))
except Exception: print('err')" "$DB" 2>/dev/null)"
fi

if [ "$CODE" = "200" ]; then
  echo "$TS OK http=200 procs=$NPROC lock=$LOCK last_scan_age=$LASTSCAN" >> "$LOG"
else
  echo "$TS DOWN http=$CODE procs=$NPROC lock=$LOCK last_scan_age=$LASTSCAN" >> "$LOG"
  echo "[QUOTEX WATCHDOG] $TS servidor NO responde (http=$CODE, procs=$NPROC)"
fi
