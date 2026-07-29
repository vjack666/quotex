"""Valida el freno (muerte del impulso) contra las cajas negras REALES del bot.

Paso 1 de la auditoria: en lugar de datos prestados (SMC-SYSTEMS), usamos
las black_box_strat_*.db que el bot YA grabo en OTC real. Cada scan_candidate
trae candles_15m (20 velas, claves ts/o/h/l/c). Por activo juntamos todas sus
velas, dedup por ts, ordenamos, y corremos brake_eval.compute_brake_and_rebote.

NO toca el bot vivo. Solo lectura de data/db/*.db. Cero reloj de pared.

Uso:
  python scripts/validar_freno_blackbox.py            # todas las cajas
  python scripts/validar_freno_blackbox.py 2026-07-20  # solo una fecha
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from strategy_lab import brake_eval as be

DB_DIR = Path("data/db")
BRAKE_CFG = {
    "stochastic": {"k": 14, "d": 3, "smooth": 3},
    "impulse": {"window": 8, "min_pips": 30},
    "brake": {"fwd": 3, "max_advance_frac": 0.10, "require_alternation": True},
    "rebote": {"fwd": 3, "min_pips": 8},
}


def _load_asset_series(db_path: Path) -> dict[str, list[tuple]]:
    """Devuelve {asset: [(ts,o,h,l,c), ...]} ordenado y dedup por ts."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT asset, candles_15m FROM scan_candidates "
            "WHERE candles_15m IS NOT NULL"
        ).fetchall()
    finally:
        con.close()

    by_asset: dict[str, dict[float, tuple]] = defaultdict(dict)
    for asset, raw in rows:
        try:
            arr = json.loads(raw)
        except (TypeError, ValueError):
            continue
        for c in arr or []:
            try:
                ts = float(c["ts"])
                o, h, l, cc = float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"])
            except (KeyError, TypeError, ValueError):
                continue
            by_asset[asset][ts] = (ts, o, h, l, cc)
    return {a: [v for v in sorted(d.values())] for a, d in by_asset.items()}


def _winrate_on_series(open_, high, low, close) -> dict:
    feat = be.compute_brake_and_rebote(open_, high, low, close, BRAKE_CFG)
    return be.brake_winrate(feat)


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    dbs = sorted(DB_DIR.glob("black_box_strat_*.db"))
    if only:
        dbs = [d for d in dbs if only in d.name]
    if not dbs:
        print("No hay cajas negras que coincidan.")
        return

    tot_n = tot_up = tot_dn = n_up = n_dn = 0
    assets_ok = 0
    per_asset = []
    for db in dbs:
        series = _load_asset_series(db)
        for asset, rows in series.items():
            if len(rows) < 30:  # necesita horma para el freno (window 8 + fwd 3)
                continue
            ts, o, h, l, c = zip(*rows)
            feat = be.compute_brake_and_rebote(
                np.array(o), np.array(h), np.array(l), np.array(c), BRAKE_CFG
            )
            r = be.brake_winrate(feat)
            if r["n"] == 0:
                continue
            assets_ok += 1
            per_asset.append((asset, r["n"], r["wr"]))
            tot_n += r["n"]
            tot_up += r["n_up"]
            tot_dn += r["n_dn"]
            n_up += r["wr_up"] * r["n_up"]
            n_dn += r["wr_dn"] * r["n_dn"]

    if tot_n == 0:
        print("Sin señales del freno en las cajas seleccionadas.")
        return

    wr_up = (n_up / tot_up) if tot_up else 0.0
    wr_dn = (n_dn / tot_dn) if tot_dn else 0.0
    wr_total = (n_up + n_dn) / tot_n
    print("=" * 60)
    print("FRENO vs CAJAS NEGRAS REALES DEL BOT (OTC, tu entorno)")
    print("=" * 60)
    print(f"Cajas leidas      : {len(dbs)}")
    print(f"Activos con horma : {assets_ok}")
    print(f"Señales totales   : {tot_n}")
    print(f"WR total          : {wr_total:.4f}  (vs 0.9105 referencia SMC-SYSTEMS)")
    print(f"WR CALL (up)      : {wr_up:.4f}  (n={tot_up})")
    print(f"WR PUT  (dn)      : {wr_dn:.4f}  (n={tot_dn})")
    margen = wr_total - 0.5405  # break-even a 85% payout
    print(f"Margen sobre BE   : {margen:+.4f}")
    print("-" * 60)
    print("Top 8 activos por WR (min 20 señales):")
    pa = [(a, n, wr) for a, n, wr in per_asset if n >= 20]
    pa.sort(key=lambda x: -x[2])
    for a, n, wr in pa[:8]:
        print(f"  {a:14s} n={n:4d} wr={wr:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
