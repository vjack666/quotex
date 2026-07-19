"""Watchdog del bot Quotex — mantiene el bot vivo 24/7.

Uso: python scripts/watchdog_bot.py
Se ejecuta como cron cada 5 min (proceso efímero). Si el bot no responde la
API o el log muestra caída de conexión reciente, hace cleanup + reinicio.

NO mata un bot sano. Deja registro en scripts/watchdog.log.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

QUOTEX_DIR = r"C:\Users\v_jac\Desktop\QUOTEX"
LOG_PATH = os.path.join(QUOTEX_DIR, "consolidation_bot.log")
WATCHDOG_LOG = os.path.join(QUOTEX_DIR, "scripts", "watchdog.log")
API_URL = "http://127.0.0.1:8080/"
START_BAT = os.path.join(QUOTEX_DIR, "start_webapp.bat")
CLEANUP = os.path.join(QUOTEX_DIR, "scripts", "cleanup_webapp_orphans.ps1")

# Errores que indican que el bot se colgó y requiere reinicio.
TRIGGER_MARKERS = ("Connection to remote host was lost",)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def wlog(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line)
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def api_alive() -> bool:
    try:
        urllib.request.urlopen(API_URL, timeout=8).status
        return True
    except Exception:
        return False


def recent_connection_lost() -> bool:
    """True si en las últimas ~7 min el log tiene un marcador de caída."""
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-200:]
    except Exception:
        return False
    cutoff = time.time() - 7 * 60
    for ln in lines:
        if any(m in ln for m in TRIGGER_MARKERS):
            # Extraer timestamp "HH:MM:SS" del inicio de línea si existe.
            try:
                ts = ln.split("[INFO]")[0].split("[ERROR]")[0].strip()
                hh, mm, ss = ts.split(":")
                # Asumimos mismo día; comparación tosca contra ahora local.
                import datetime as _dt
                line_t = _dt.datetime.strptime(
                    _dt.datetime.now().strftime("%Y-%m-%d ") + f"{hh}:{mm}:{ss}",
                    "%Y-%m-%d %H:%M:%S",
                ).timestamp()
                if line_t >= cutoff:
                    return True
            except Exception:
                # Si no parsea el timestamp, asumimos reciente (línea en tail).
                return True
    return False


def proc_alive() -> bool:
    try:
        out = subprocess.run(
            [
                "powershell", "-Command",
                "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                "Where-Object { $_.CommandLine -like '*app.py*' }) { 'HAY' } else { 'NO' }",
            ],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        return out == "HAY"
    except Exception:
        return False


def start_bot() -> None:
    subprocess.Popen(
        ["cmd.exe", "/c", START_BAT],
        cwd=QUOTEX_DIR,
        creationflags=0x00000008,  # DETACHED_PROCESS
    )


def restart(reason: str) -> None:
    wlog(f"REINICIO requerido ({reason}). Cleanup + arranque.")
    try:
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", CLEANUP],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as exc:
        wlog(f"cleanup error: {exc}")
    time.sleep(5)
    start_bot()
    time.sleep(12)
    # Arrancar el loop de escaneo.
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8080/api/bot/start",
            data=b"{}", headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=10).read()
        wlog("bot/start enviado. Loop reiniciado.")
    except Exception as exc:
        wlog(f"bot/start falló (el server puede tardar): {exc}")


def main() -> int:
    alive = api_alive()
    wlog(f"check: api_alive={alive} proc_alive={proc_alive()} conn_lost_reciente={recent_connection_lost()}")
    if not alive or recent_connection_lost():
        restart("api_down" if not alive else "conn_lost")
        return 0
    wlog("bot sano, nada que hacer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
