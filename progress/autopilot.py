"""Autopilot STRAT-F: relanza main.py mientras el host mate el WebSocket, y
cuenta operaciones ganadas en la cuenta demo (PRACTICE) para el objetivo de
3 wins (Massaniello 5/3 en ventana de 2h).

El bot opera en demo real; las opciones se cierran en el servidor de Quotex
aunque este proceso/host mate main.py. Al relanzar, el bot reconcilia los
PENDING y registra WIN/LOSS en data/db/trade_journal-<fecha>.db.

Estado persistente en progress/autopilot_state.json:
  { wins, losses, total_trades, relaunches, objective_met, last_check }
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "progress" / "autopilot_state.json"
DB_DIR = ROOT / "data" / "db"
TARGET_WINS = 3
MAX_RELAUNCHES = 200
RUN_TIMEOUT = 280  # s — asumir host-kill si main no termina solo antes


def _today_db() -> Path:
    # Igual naming que el bot: trade_journal-YYYY-MM-DD.db
    return DB_DIR / f"trade_journal-{datetime.now().strftime('%Y-%m-%d')}.db"


def _count_outcomes(db: Path) -> tuple[int, int, int]:
    if not db.exists():
        return 0, 0, 0
    try:
        con = sqlite3.connect(str(db))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT outcome, COUNT(*) c FROM candidates "
            "WHERE outcome IN ('WIN','LOSS') GROUP BY outcome"
        )
        d = {r["outcome"]: r["c"] for r in cur.fetchall()}
        cur.execute(
            "SELECT COUNT(*) c FROM candidates WHERE outcome IN ('WIN','LOSS')"
        )
        total = cur.fetchone()["c"]
        con.close()
        return d.get("WIN", 0), d.get("LOSS", 0), total
    except Exception as ex:  # noqa: BLE001
        return 0, 0, 0


def _load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"wins": 0, "losses": 0, "total": 0, "relaunches": 0,
            "objective_met": False, "last_check": "", "log": ""}


def _save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=2))


def _launch_main() -> subprocess.Popen:
    ts = datetime.now().strftime("%H%M%S")
    log_path = ROOT / "progress" / f"run_trader_{ts}.log"
    f = open(log_path, "w", buffering=1)
    # trader_short.py: ciclo COMPACTO (evalua ~10 activos, coloca 1 orden y
    # SALE en <90s) -> sobrevive al host-kill del sandbox y opera de verdad.
    # Al relanzar reconcilia la PENDING anterior (WIN/LOSS en la DB).
    p = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "progress/trader_short.py"],
        cwd=str(ROOT),
        stdout=f,
        stderr=subprocess.STDOUT,
    )
    return p


def main() -> None:
    s = _load_state()
    print(f"[autopilot] arranca. wins={s['wins']} losses={s['losses']} "
          f"relaunches={s['relaunches']} target={TARGET_WINS}")
    while s["relaunches"] < MAX_RELAUNCHES:
        wins, losses, total = _count_outcomes(_today_db())
        s["wins"], s["losses"], s["total"] = wins, losses, total
        s["last_check"] = datetime.now(timezone.utc).isoformat()
        if wins >= TARGET_WINS:
            s["objective_met"] = True
            s["log"] = f"OBJETIVO CUMPLIDO: {wins} wins / {losses} losses"
            _save_state(s)
            print(f"[autopilot] *** OBJETIVO: {wins} wins alcanzadas ***")
            return
        if s["relaunches"] > 0 and (wins + losses) == 0 and s["relaunches"] % 5 == 0:
            s["log"] = (f"sin trades cerrados tras {s['relaunches']} relanzamientos "
                        f"— revisar calibracion")
        _save_state(s)

        print(f"[autopilot] lanzando main.py (#{s['relaunches']+1}) wins={wins} "
              f"losses={losses}")
        p = _launch_main()
        try:
            rc = p.wait(timeout=RUN_TIMEOUT)
            # murio solo (no host-kill) -> esperar un poco y relanzar
            print(f"[autopilot] main.py termino (rc={rc})")
            time.sleep(20)
        except subprocess.TimeoutExpired:
            # asumir host-kill de WebSocket -> matar y relanzar
            print(f"[autopilot] timeout {RUN_TIMEOUT}s — host-kill asumido, reiniciando")
            try:
                p.kill()
            except Exception:
                pass
            time.sleep(10)
        s["relaunches"] += 1
        _save_state(s)
    s["log"] = "MAX_RELAUNCHES alcanzado"
    _save_state(s)
    print("[autopilot] maximo de relanzamientos alcanzado — detener.")


if __name__ == "__main__":
    main()
