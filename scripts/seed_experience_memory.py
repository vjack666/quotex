"""Seed OFFLINE del Experience Engine desde datos ya persistidos.

RE-LEE scan_candidates de data/db/*.db (que ya guarda velas + estocástico + outcome)
y construye arcos de experiencia del mercado, escribiéndolos en la memoria única
(data/market_memory/, append-only). NO toca el bot en vivo.

Uso:
    py scripts/seed_experience_memory.py              # sembra todas las DBs
    py scripts/seed_experience_memory.py --report     # también imprime validación
    py scripts/seed_experience_memory.py --db ruta.db  # solo una DB

El seed es idempotente: la memoria dedup por fingerprint.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Asegurar que src/ esté importable al correr el script suelto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from experience_engine import ExperienceMemory
from experience_schema import MarketExperience

DB_DIR = Path("data/db")


def _json(x: Any) -> Optional[Any]:
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    try:
        return json.loads(x)
    except Exception:
        return None


def _stoch_level(stoch: Optional[dict]) -> Dict[str, Any]:
    if not stoch:
        return {}
    return {
        "zone": stoch.get("estado"),
        "k": stoch.get("k"),
        "d": stoch.get("d"),
        "cruce": stoch.get("cruce"),
        "divergencia": stoch.get("divergencia"),
    }


def _hour_dow(ts: float) -> Dict[str, int]:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return {"hour_utc": dt.hour, "dow": dt.weekday()}


def _pips(entry: Optional[float], exit_: Optional[float], direction: str) -> Optional[float]:
    if not entry or not exit_:
        return None
    raw = (exit_ - entry) * (1.0 if direction == "CALL" else -1.0)
    # velas FX ~5 decimales; pips = raw*1e4 (aprox, suficiente para validación)
    return round(raw * 10000.0, 1)


def build_experience(row: sqlite3.Row) -> Optional[MarketExperience]:
    """Construye un arco de experiencia desde una fila de scan_candidates.

    Tolerante a columnas faltantes (distintas versiones de la DB).
    """
    try:
        r = dict(row)  # sqlite3.Row -> dict (tipado y .get limpio)
        direction = (r.get("direction") or "").upper()
        if direction not in ("CALL", "PUT"):
            return None
        ts = float(r.get("ts") or 0)
        if not ts:
            return None

        sd = _json(r.get("strategy_details")) or {}
        stoch15 = _json(r.get("stoch_m15")) or {}
        stoch5 = _json(r.get("stoch_m5")) or {}
        stoch1 = _json(r.get("stoch_m1")) or {}

        # ── contexto_previo (TAL CUAL, sin etiquetar soporte/resistencia) ──
        ctx = {
            "stoch_m15": _stoch_level(stoch15),
            "stoch_m5": _stoch_level(stoch5),
            "stoch_m1": _stoch_level(stoch1),
            "structure_ctx": sd.get("ctx"),
            "event_pattern": sd.get("event"),
            "pattern": sd.get("pattern"),
            "score_static": r.get("score"),
            **_hour_dow(ts),
        }

        # ── evento ──
        last = None
        candles15 = _json(r.get("candles_15m")) or []
        if candles15:
            last = candles15[-1]
        level = r.get("entry_price") or (last.get("c") if last else None)
        evento = {
            "tipo": "entrada",
            "direccion": direction,
            "nivel": level,
            "payout": r.get("payout"),
            "duration_sec": r.get("duration_sec"),
            "decision_scan": r.get("decision"),
        }

        # ── evolucion + resultado (desde outcome) ──
        order_result = (r.get("order_result") or "").upper()
        profit = r.get("profit")
        entry = r.get("entry_price")
        exit_ = r.get("exit_price")
        pips = _pips(entry, exit_, direction)
        evolucion = {
            "pips_recorridos": pips,
            "tiempo_a_invalidacion_s": r.get("duration_sec"),
            "loss_reason": r.get("loss_reason"),
        }
        resultado = {
            "decision": order_result if order_result in ("WIN", "LOSS") else None,
            "pips_netos": pips,
            "profit": profit,
        }

        consecuencias = {
            "improvement_hint": r.get("improvement_hint"),
            "loss_reason": r.get("loss_reason"),
        }

        raw = {
            "candles_15m": candles15,
            "candles_5m": _json(r.get("candles_5m")),
            "candles_1m": _json(r.get("candles_1m")),
        }

        return MarketExperience(
            ts=int(ts),
            asset=r.get("asset") or "",
            tf="M15",
            contexto_previo=ctx,
            evento=evento,
            evolucion=evolucion,
            resultado=resultado,
            consecuencias=consecuencias,
            raw=raw,
        )
    except Exception:
        return None


def seed_db(db_path: Path, mem: ExperienceMemory, only_resolved: bool = True) -> int:
    con = sqlite3.connect(str(db_path), timeout=5.0)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT * FROM scan_candidates WHERE order_result IN ('WIN','LOSS')"
            if only_resolved else
            "SELECT * FROM scan_candidates"
        ).fetchall()
    except Exception:
        return 0
    finally:
        con.close()

    n = 0
    for r in rows:
        exp = build_experience(r)
        if exp and mem.record(exp):
            n += 1
    return n


def _report(mem: ExperienceMemory) -> None:
    exps = mem.all_experiences()
    closed = [e for e in exps if e.is_closed()]
    if not closed:
        print("Sin experiencias cerradas para reportar.")
        return
    wins = [e for e in closed if e.resultado.get("decision") == "WIN"]
    wr = len(wins) / len(closed)
    print(f"\n=== Experience Engine — reporte OFFLINE ===")
    print(f"Experiencias totales: {len(exps)} | cerradas (con outcome): {len(closed)}")
    print(f"Win rate global: {wr:.1%} ({len(wins)}/{len(closed)})")

    # Validación temprana (R6/R8): ¿el contexto (estado stoch + ctx estructura)
    # correlaciona con win rate? Agrupamos por (stoch_m15_estado, structure_ctx).
    groups: Dict[tuple, List[MarketExperience]] = {}
    for e in closed:
        key = (
            e.contexto_previo.get("stoch_m15", {}).get("zone"),
            e.contexto_previo.get("structure_ctx"),
        )
        groups.setdefault(key, []).append(e)
    print("\nWin rate por contexto (estado stoch | ctx estructura):")
    for key, lst in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(lst) < 5:
            continue
        w = sum(1 for e in lst if e.resultado.get("decision") == "WIN")
        print(f"  {str(key):45s} n={len(lst):4d}  WR={w/len(lst):.1%}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default=None, help="solo una DB")
    ap.add_argument("--report", action="store_true", help="imprime validación")
    args = ap.parse_args()

    mem = ExperienceMemory()
    total = 0
    if args.db:
        dbs = [Path(args.db)]
    else:
        dbs = sorted(DB_DIR.glob("*.db"))
    for db in dbs:
        n = seed_db(db, mem)
        total += n
        print(f"  {db.name}: +{n} experiencias")
    print(f"Total sembradas: {total} | memoria en {mem.root}")

    if args.report:
        _report(mem)


if __name__ == "__main__":
    main()
