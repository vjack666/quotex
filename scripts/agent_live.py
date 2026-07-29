"""Agente VIVO de aprendizaje STRAT-F (modo laboratorio, determinista).

Punto 2 de Ruben (2026-07-24): el agente debe estar VIVO, consciente de
los trades en tiempo real, y responderse las preguntas necesarias para
mejorar el sistema aprendiendo de ganancias y perdidas.

Diseno:
- ``poll_once()`` carga los trades resueltos NUEVOS desde la ultima vez
  (usando un ``last_seen_id`` persistente en ``live_memory.json``).
- Por cada trade nuevo el agente:
    * acumula en memoria incremental (winrate global + por celda
      direction x TF x tendencia),
    * se hace AUTO-PREGUNTAS y se las responde (¿gane/perdi? ¿el patron
      del estocastico predijo bien? ¿que debo mejorar?),
    * guarda el hallazgo en ``live_memory.json`` (durable, pequeno).
- Reusa ``agent_stoch.analyze`` y ``agent_review.analyze`` para el
  analisis profundo cada vez que acumula ``DEEP_EVERY`` trades nuevos.
- El hook en ``black_box_recorder.record_order_result`` llama a
  ``on_trade_resolved`` en un hilo daemon (no bloquea el bot).

No usa LLM: es algebra determinista sobre trades resueltos. No modifica
el bot ni envia ordenes; solo lee/escribe su propia memoria.

Uso:
  .venv/Scripts/python.exe scripts/agent_live.py --once
  .venv/Scripts/python.exe scripts/agent_live.py --watch --interval 30
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, "src")
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent_common as ac  # noqa: E402

MEMORY_PATH = os.path.join(_ROOT, "data", "agent", "live_memory.json")
DEEP_EVERY = 10  # cada N trades nuevos, analisis profundo con agent_stoch/review


# ── Carga incremental de trades nuevos ───────────────────────────────────────
def _db_paths() -> list[str]:
    """Devuelve las DBs de black_box ordenadas (las del dia primero)."""
    import glob
    dbs = sorted(glob.glob(os.path.join(_ROOT, "data", "db", "black_box_strat*.db")))
    return dbs


def load_new_trades(last_seen_id: int) -> tuple[list[dict], int]:
    """Carga trades resueltos con rowid > last_seen_id de todas las DBs.

    Devuelve (trades, max_id). Cada trade: {id, asset, direction,
    order_result, stoch:{m15,m5,m1}}.
    """
    trades: list[dict] = []
    max_id = last_seen_id
    for db in _db_paths():
        try:
            con = sqlite3.connect(db)
            cur = con.cursor()
            cols = [d[1] for d in cur.execute("PRAGMA table_info(scan_candidates)")]
            if "order_result" not in cols:
                con.close()
                continue
            has_m5 = "stoch_m5" in cols
            has_m1 = "stoch_m1" in cols
            sel = (
                "SELECT rowid, asset, direction, order_result, stoch_m15"
                + (", stoch_m5" if has_m5 else "")
                + (", stoch_m1" if has_m1 else "")
                + " FROM scan_candidates WHERE order_result IN ('WIN','LOSS') AND rowid > ?"
            )
            for row in cur.execute(sel, (last_seen_id,)).fetchall():
                rid = row[0]
                asset = row[1]
                direction = (row[2] or "").upper()
                outcome = row[3]
                stoch: dict[str, Any] = {}
                if row[4]:
                    try:
                        stoch["m15"] = json.loads(row[4])
                    except (json.JSONDecodeError, TypeError):
                        stoch["m15"] = {}
                if has_m5 and row[5]:
                    try:
                        stoch["m5"] = json.loads(row[5])
                    except (json.JSONDecodeError, TypeError):
                        stoch["m5"] = {}
                if has_m1 and row[6]:
                    try:
                        stoch["m1"] = json.loads(row[6])
                    except (json.JSONDecodeError, TypeError):
                        stoch["m1"] = {}
                trades.append({
                    "id": rid,
                    "asset": asset,
                    "direction": direction,
                    "order_result": outcome,
                    "stoch": stoch,
                })
                if rid > max_id:
                    max_id = rid
            con.close()
        except (sqlite3.OperationalError, FileNotFoundError):
            continue
    return trades, max_id


# ── Memoria viva (incremental, durable) ────────────────────────────────────
def load_memory() -> dict:
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _empty_memory() -> dict:
    return {
        "n_total": 0,
        "n_win": 0,
        "winrate": 0.0,
        "cells": {},          # "CALL|M15:bajando" -> {n, w, wr}
        "last_seen_id": 0,
        "last_questions": [],  # ultimas N auto-preguntas
        "deep_runs": 0,
        "updated_at": "",
    }


def _cell_key(t: dict) -> str:
    parts = []
    for tf in ("m15", "m5", "m1"):
        trend = ac.stoch_trend(t["stoch"].get(tf, {}))
        if trend != "n/a" and ac.stoch_zone_label(t["stoch"].get(tf, {})) != "n/a":
            parts.append(f"{tf.upper()}:{trend}")
    return f"{t['direction']}|" + " ".join(parts) if parts else f"{t['direction']}|n/a"


def _ask_questions(t: dict, mem: dict) -> list[dict]:
    """El agente se responde las preguntas para mejorar."""
    qa: list[dict] = []
    won = t["order_result"] == "WIN"
    cell = _cell_key(t)
    cell_stat = mem["cells"].get(cell, {"n": 0, "w": 0, "wr": 0.0})

    # P1: ¿gane o perdi y por que (segun el patron del estocastico)?
    trend_m15 = ac.stoch_trend(t["stoch"].get("m15", {}))
    zone_m15 = ac.stoch_zone_label(t["stoch"].get("m15", {}))
    if won:
        why = (f"GANE. Estocastico M15 estaba en tendencia '{trend_m15}' "
               f"y zona '{zone_m15}'. El patron era favorable.")
    else:
        why = (f"PERDI. Estocastico M15 estaba en tendencia '{trend_m15}' "
               f"y zona '{zone_m15}'. O el patron no predicjo, o hubo ruido "
               f"de broker/externo.")
    qa.append({
        "q": f"¿Por que {('gane' if won else 'perdi')} este trade ({t['direction']} {t['asset']})?",
        "a": why,
    })

    # P2: ¿el patron del estocastico predijo bien?
    # Si gane y la celda tenia wr alta -> prediccio bien. Si perdi y wr alta -> fallo.
    pred = "si" if (won and cell_stat["wr"] >= 0.55) or (not won and cell_stat["wr"] <= 0.45) else "no"
    qa.append({
        "q": f"¿El patron {cell} (wr={cell_stat['wr']*100:.0f}%, n={cell_stat['n']}) predijo bien?",
        "a": f"{pred} (wr acumulada de la celda vs resultado real).",
    })

    # P3: ¿que debo mejorar?
    if not won and cell_stat["n"] >= 20 and cell_stat["wr"] < 0.45:
        improve = (f"La celda {cell} es perdedora sistemica (wr={cell_stat['wr']*100:.0f}%). "
                   f"Mejorar: no operar esta configuracion, o exigir confirmacion extra.")
    elif won and cell_stat["n"] >= 20 and cell_stat["wr"] >= 0.60:
        improve = f"La celda {cell} es ganadora sistemica. Mejorar: aumentar exposicion / priorizarla."
    else:
        improve = ("Muestra aun pequena (n=%d) o ruido. Mejorar: acumular mas trades antes "
                   "de decidir." % cell_stat["n"])
    qa.append({"q": "¿Que debo mejorar en el sistema?", "a": improve})

    return qa


def _update_memory(mem: dict, trades: list[dict]) -> dict:
    for t in trades:
        mem["n_total"] += 1
        won = t["order_result"] == "WIN"
        if won:
            mem["n_win"] += 1
        cell = _cell_key(t)
        cs = mem["cells"].setdefault(cell, {"n": 0, "w": 0, "wr": 0.0})
        cs["n"] += 1
        if won:
            cs["w"] += 1
        cs["wr"] = round(cs["w"] / cs["n"], 4)
        # auto-preguntas (guardar solo las ultimas 5)
        qs = _ask_questions(t, mem)
        mem["last_questions"].insert(0, {
            "id": t["id"],
            "asset": t["asset"],
            "direction": t["direction"],
            "outcome": t["order_result"],
            "ts": datetime.now(timezone.utc).isoformat(),
            "qa": qs,
        })
        mem["last_questions"] = mem["last_questions"][:5]
    mem["winrate"] = round(mem["n_win"] / mem["n_total"], 4) if mem["n_total"] else 0.0
    return mem


# ── API publica ───────────────────────────────────────────────────────────
def poll_once() -> dict:
    """Procesa trades nuevos y actualiza la memoria viva. Devuelve resumen."""
    mem = load_memory() or _empty_memory()
    last = mem.get("last_seen_id", 0)
    trades, max_id = load_new_trades(last)
    if trades:
        mem = _update_memory(mem, trades)
        mem["last_seen_id"] = max_id
    mem["updated_at"] = datetime.now(timezone.utc).isoformat()
    # Analisis profundo cada DEEP_EVERY trades nuevos.
    if len(trades) >= DEEP_EVERY or (mem["n_total"] and mem["n_total"] % DEEP_EVERY == 0):
        try:
            import agent_stoch
            from agent_common import load_resolved_trades
            all_trades = load_resolved_trades()
            deep = agent_stoch.analyze_stoch(all_trades)
            mem["deep_runs"] = mem.get("deep_runs", 0) + 1
            mem["deep_last"] = {
                "n": deep.get("n"),
                "winrate": deep.get("winrate"),
                "hypothesis_call_m15_down_wr": deep.get("direction_x_m15_trend", {})
                    .get("CALL|M15:bajando", {}).get("wr"),
            }
        except Exception as exc:  # nosec - nunca debe romper el bot
            mem["deep_error"] = str(exc)
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(mem, fh, indent=2)
    return {"new_trades": len(trades), "n_total": mem["n_total"],
            "winrate": mem["winrate"], "questions": len(mem["last_questions"])}


def on_trade_resolved(order_id: str = "", outcome: str = "") -> None:
    """Hook fire-and-forget llamado desde black_box_recorder.

    Corre en hilo daemon para no bloquear el bot. Solo hace un poll.
    """
    try:
        poll_once()
    except Exception as exc:  # nosec - el agente nunca debe romper el bot
        sys.stderr.write(f"[AGENT_LIVE] poll fallo: {exc}\n")


def render_report(mem: dict) -> str:
    L: list[str] = []
    L.append("# Agente VIVO STRAT-F — memoria de aprendizaje en tiempo real")
    L.append(f"\nGenerado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    L.append(f"Trades aprendidos: {mem.get('n_total', 0)} | WIN: {mem.get('n_win', 0)} "
             f"| winrate: {mem.get('winrate', 0)*100:.1f}%")
    L.append("\n## Celdas direction x TF x tendencia (top por n)")
    cells = sorted(mem.get("cells", {}).items(), key=lambda kv: kv[1]["n"], reverse=True)
    for k, v in cells[:12]:
        L.append(f"- {k}: n={v['n']} wr={v['wr']*100:.1f}%")
    L.append("\n## Ultimas auto-preguntas del agente")
    for item in mem.get("last_questions", [])[:5]:
        L.append(f"\n[Trade #{item['id']} {item['direction']} {item['asset']} "
                 f"→ {item['outcome']}]")
        for qa in item["qa"]:
            L.append(f"  • {qa['q']}")
            L.append(f"    → {qa['a']}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Agente vivo de aprendizaje STRAT-F.")
    ap.add_argument("--once", action="store_true", help="Un solo poll y sale.")
    ap.add_argument("--watch", action="store_true", help="Loop de poll cada --interval s.")
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--report", action="store_true", help="Imprime reporte al final.")
    args = ap.parse_args()

    if args.once:
        res = poll_once()
        print(f"[AGENT_LIVE] nuevo={res['new_trades']} total={res['n_total']} "
              f"wr={res['winrate']*100:.1f}%")
    elif args.watch:
        print(f"[AGENT_LIVE] watch cada {args.interval}s (Ctrl+C para salir)...")
        try:
            while True:
                res = poll_once()
                if res["new_trades"]:
                    print(f"[AGENT_LIVE] +{res['new_trades']} trades → "
                          f"total={res['n_total']} wr={res['winrate']*100:.1f}%")
                import time
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("[AGENT_LIVE] detenido.")
    if args.report:
        print(render_report(load_memory()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
