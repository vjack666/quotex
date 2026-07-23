"""ML training progress tracker for Feature #18 (lightgbm_scorer).

Counts resolved STRAT-F trades across the black-box DBs using the SAME
criteria as train_lightgbm.py (sources: trade_journal-*.db -> candidates
(outcome WIN/LOSS, strategy_origin='STRAT-F'); black_box_strat*.db ->
scan_candidates (order_result WIN/LOSS, strategy='STRAT-F')).

ML_COLLECTION_START bandera (src/config.py): si está fijada ("YYYY-MM-DD
HH:MM:SS"), el conteo del BATCH NUEVO solo cuenta trades resueltos con
created_at >= esa fecha (la campaña de recolección activa). Con "" cuenta
todo el histórico.

Prints how many trades are resolved vs the MIN_TRADES=500 hard guard, and
how many are still missing before `python scripts/train_lightgbm.py` will
actually train.

Safe to run anytime: read-only, no data collection, no training.
Usage:
    python scripts/ml_progress.py
"""
from __future__ import annotations

import glob
import os
import sqlite3

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

MIN_TRADES = 500  # must match train_lightgbm.MIN_TRADES
DB_GLOB_CANDIDATES = os.path.join(_ROOT, "data", "db", "trade_journal-*.db")
DB_GLOB_BLACKBOX = os.path.join(_ROOT, "data", "db", "black_box_strat*.db")

# Bandera de recolección: fecha/hora/minuto desde la que se cuenta el batch
# nuevo. Leída de config (fallback "" = sin bandera, cuenta todo).
try:
    import sys
    sys.path.insert(0, os.path.join(_ROOT, "src"))
    import config as _cfg  # noqa: E402
    ML_COLLECTION_START = getattr(_cfg, "ML_COLLECTION_START", "") or ""
except Exception:
    ML_COLLECTION_START = ""


def _discover_db_paths() -> list[str]:
    """Unique, existing DB paths that hold black-box trades.

    Mirrors train_lightgbm.discover_db_paths: de-duplicates and skips the
    empty data/trade_journal.db.
    """
    paths: list[str] = []
    seen = set()
    for pattern in (DB_GLOB_CANDIDATES, DB_GLOB_BLACKBOX):
        for p in sorted(glob.glob(pattern)):
            ap = os.path.abspath(p)
            if ap in seen:
                continue
            seen.add(ap)
            paths.append(p)
    return paths


def _norm_ts(ts: str | None) -> str:
    """Normaliza un created_at a 'YYYY-MM-DD HH:MM:SS' para comparar con la bandera."""
    if not ts:
        return ""
    return str(ts).replace("T", " ").strip()[:19]


def count_resolved(db_paths: list[str]) -> tuple[int, int, list[tuple[str, int, int]]]:
    """Devuelve (total_global, total_batch, per_db[(nombre, global, batch)]).

    total_batch solo cuenta fila con created_at >= ML_COLLECTION_START
    (si la bandera está fijada). Con bandera "" ambos coinciden.
    """
    total_global = 0
    total_batch = 0
    per: list[tuple[str, int, int]] = []
    flag = _norm_ts(ML_COLLECTION_START)
    for db in db_paths:
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
        except sqlite3.Error:
            continue
        g = 0
        b = 0
        # trade_journal: candidates (sin columna de timestamp -> solo global)
        try:
            cur.execute(
                "SELECT COUNT(*) FROM candidates "
                "WHERE outcome IN ('WIN','LOSS') AND strategy_origin='STRAT-F'"
            )
            g += cur.fetchone()[0]
        except sqlite3.Error:
            pass
        # black_box: scan_candidates (created_at disponible -> filtrable)
        try:
            cur.execute(
                "SELECT COUNT(*) FROM scan_candidates "
                "WHERE order_result IN ('WIN','LOSS') AND strategy='STRAT-F'"
            )
            g += cur.fetchone()[0]
            if flag:
                cur.execute(
                    "SELECT COUNT(*) FROM scan_candidates "
                    "WHERE order_result IN ('WIN','LOSS') AND strategy='STRAT-F' "
                    "AND created_at >= ?",
                    (flag,),
                )
                b += cur.fetchone()[0]
        except sqlite3.Error:
            pass
        conn.close()
        if g:
            per.append((os.path.basename(db), g, b))
            total_global += g
            total_batch += b
    if not flag:
        total_batch = total_global  # sin bandera: batch = todo
    return total_global, total_batch, per


def main() -> None:
    db_paths = _discover_db_paths()
    total_global, total_batch, per = count_resolved(db_paths)

    if ML_COLLECTION_START:
        print(f"Bandera ML_COLLECTION_START = {ML_COLLECTION_START}")
        print(f"Trades resueltos (batch nuevo desde bandera) = {total_batch}")
        batch = total_batch
    else:
        print("Bandera ML_COLLECTION_START = (vacía) — contando histórico completo")
        batch = total_global

    print("Resolved STRAT-F trades (ML training guard):")
    for name, g, b in sorted(per):
        if ML_COLLECTION_START:
            print(f"  {name}: global={g}  batch={b}")
        else:
            print(f"  {name}: {g}")
    print(f"\nTOTAL resolved STRAT-F (batch) = {batch}")
    print(f"MIN_TRADES guard      = {MIN_TRADES}")

    if batch >= MIN_TRADES:
        print(f"\n✅ READY: {batch} >= {MIN_TRADES}. Run: python scripts/train_lightgbm.py")
    else:
        missing = MIN_TRADES - batch
        print(f"\n⏳ NOT READY: missing {missing} more trades before ML can train.")
        print(f"   Run `python scripts/train_lightgbm.py` once >= {MIN_TRADES}.")


if __name__ == "__main__":
    main()
