"""Supervisor del bot CONSOLIDATION en vivo (LIVE, DEMO).

- Detecta si el bot esta vivo revisando la antiguedad del log rotativo
  (data/logs/runtime/consolidation_bot.log): si no se escribe hace >2 min,
  se asume caido.
- Si esta caido, lo relanza en LIVE (--live) usando el venv.
- Si en el log aparece el error ya corregido del pool roto
  ("grupo de procesos se rompio" / "[STRAT-F][parallel] fallo"), lo registra
  en supervisor_alerts.log para investigacion.
- Escribe su propio estado a supervisor.log.

No cambia ninguna config del bot (duration_min, etc.). Solo lo mantiene vivo.
"""
from __future__ import annotations

import subprocess
import time
import os
from pathlib import Path

# El supervisor vive en ~/.hermes/scripts pero opera sobre el repo QUOTEX.
BASE = Path(r"C:\Users\v_jac\Desktop\QUOTEX")
LOG = BASE / "data" / "logs" / "runtime" / "consolidation_bot.log"
VENV_PY = BASE / ".venv" / "Scripts" / "python.exe"
BOT_MODULE = "consolidation_bot"
SUP_LOG = BASE / "supervisor.log"
ALERT_LOG = BASE / "supervisor_alerts.log"

STALE_SEC = 150          # si el log no se escribe en 2.5 min -> caido
POOL_ERR = "grupo de procesos se rompio"


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line)
    with open(SUP_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def bot_alive() -> bool:
    if not LOG.exists():
        return False
    age = time.time() - LOG.stat().st_mtime
    return age < STALE_SEC


def launch() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BASE / "src")
    # stdout/stderr al log del bot para no perder trazas
    out = open(BASE / "bot_live.log", "ab", buffering=1)
    subprocess.Popen(
        [str(VENV_PY), "-u", "-m", BOT_MODULE, "--live"],
        cwd=str(BASE),
        env=env,
        stdout=out,
        stderr=subprocess.STDOUT,
        close_fds=True,
    )
    log("[SUP] Relanzando bot en LIVE...")


def check_pool_error_recent() -> bool:
    if not LOG.exists():
        return False
    try:
        with open(LOG, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
    except Exception:
        return False
    # Solo las ultimas ~50KB
    tail = data[-50000:]
    if POOL_ERR in tail:
        # Verifica que no sea historico muy viejo: busca timestamp de hoy
        return POOL_ERR in tail.splitlines()[-200:]
    return False


def main() -> None:
    log("[SUP] Check arranca")
    if check_pool_error_recent():
        with open(ALERT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} ALERTA: error de pool roto reaparecio en el log\n")
        log("[SUP] ALERTA: error de pool roto detectado en log reciente")
    if bot_alive():
        log("[SUP] Bot vivo (log reciente). OK.")
    else:
        log("[SUP] Bot caido (log estancado >%.0fs). Relanzando." % STALE_SEC)
        launch()
        log("[SUP] Relanzado.")


if __name__ == "__main__":
    main()
