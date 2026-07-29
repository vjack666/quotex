"""Walk-forward fuera de muestra del freno sobre cajas negras REALES del bot.

Paso 2B de la auditoria (Constitucion: exige falsacion fuera de muestra).
- Train = dias 17-21, Test = dias 22-26 (mismos parametros fijos del freno).
- WR train vs WR test: si test ~ train, el edge es estable OOS.
- Placebo: invertir la prediccion del freno (brake_up<->brake_dn) y medir
  WR por azar. Si test >> placebo, el edge es real, no ruido de muestreo.

NO toca el bot vivo. Solo lectura de data/db/*.db. Cero reloj de pared.
"""
from __future__ import annotations

import json
import sqlite3
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
TRAIN_DAYS = ("2026-07-17", "2026-07-18", "2026-07-19", "2026-07-20", "2026-07-21")
TEST_DAYS = ("2026-07-22", "2026-07-23", "2026-07-24", "2026-07-25", "2026-07-26")


def _load_split(db_paths) -> dict[str, list[tuple]]:
    by_asset: dict[str, dict[float, tuple]] = defaultdict(dict)
    for db in db_paths:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT asset, candles_15m FROM scan_candidates "
                "WHERE candles_15m IS NOT NULL"
            ).fetchall()
        finally:
            con.close()
        for asset, raw in rows:
            try:
                arr = json.loads(raw)
            except (TypeError, ValueError):
                continue
            for c in arr or []:
                try:
                    ts = float(c["ts"]); o = float(c["o"]); h = float(c["h"])
                    l = float(c["l"]); cc = float(c["c"])
                except (KeyError, TypeError, ValueError):
                    continue
                by_asset[asset][ts] = (ts, o, h, l, cc)
    return {a: [v for v in sorted(d.values())] for a, d in by_asset.items()}


def _wr_from_rows(rows, cfg, invert=False) -> dict:
    if len(rows) < 30:
        return {"n": 0, "wr": 0.0, "n_up": 0, "wr_up": 0.0, "n_dn": 0, "wr_dn": 0.0}
    _t, o, h, l, c = zip(*rows)
    feat = be.compute_brake_and_rebote(
        np.array(o), np.array(h), np.array(l), np.array(c), cfg
    )
    if invert:
        # placebo: intercambiar la direccion predicha del rebote
        feat = dict(feat)
        feat["rebote_up"], feat["rebote_dn"] = feat["rebote_dn"], feat["rebote_up"]
    return be.brake_winrate(feat)


def _combine(res_list: list[dict]) -> dict:
    n_up = sum(r["n_up"] for r in res_list)
    n_dn = sum(r["n_dn"] for r in res_list)
    n = n_up + n_dn
    wr = (r["wr_up"] * r["n_up"] + r["wr_dn"] * r["n_dn"] for r in res_list)
    wr = sum(wr)
    wr = (wr / n) if n else 0.0
    return {"n": n, "n_up": n_up, "n_dn": n_dn, "wr": wr}


def main() -> None:
    db_all = {d: DB_DIR / f"black_box_strat_{d}.db" for d in TRAIN_DAYS + TEST_DAYS}
    missing = [d for d, p in db_all.items() if not p.exists()]
    if missing:
        print(f"Faltan cajas: {missing}")
        return

    train = _load_split([db_all[d] for d in TRAIN_DAYS])
    test = _load_split([db_all[d] for d in TEST_DAYS])

    train_res = [_wr_from_rows(r, BRAKE_CFG) for r in train.values()]
    test_res = [_wr_from_rows(r, BRAKE_CFG) for r in test.values()]
    test_placebo = [_wr_from_rows(r, BRAKE_CFG, invert=True) for r in test.values()]

    tr = _combine([r for r in train_res if r["n"]])
    te = _combine([r for r in test_res if r["n"]])
    pl = _combine([r for r in test_placebo if r["n"]])

    print("=" * 60)
    print("WALK-FORWARD FUERA DE MUESTRA — FRENO vs CAJAS REALES")
    print("=" * 60)
    print(f"Train dias 17-21 : {tr['n']:5d} señales  WR={tr['wr']:.4f}")
    print(f"Test  dias 22-26 : {te['n']:5d} señales  WR={te['wr']:.4f}")
    print(f"Placebo (invert) : {pl['n']:5d} señales  WR={pl['wr']:.4f}")
    print("-" * 60)
    delta = te["wr"] - tr["wr"]
    edge_vs_placebo = te["wr"] - pl["wr"]
    print(f"Train->Test delta : {delta:+.4f}  (estable si ~0)")
    print(f"Edge vs placebo   : {edge_vs_placebo:+.4f}  (real si >>0)")
    print(f"Margen vs BE 85%  : {te['wr']-0.5405:+.4f}")
    verdict = "EDGE ESTABLE OOS" if abs(delta) < 0.05 and edge_vs_placebo > 0.20 \
        else ("EDGE DEGRADA OOS" if edge_vs_placebo > 0.20 else "EDGE NO CLARO")
    print(f"Veredicto         : {verdict}")
    print("=" * 60)


if __name__ == "__main__":
    main()
