"""CICLO-002 — EXP-082/083: composicion en SPOT M15 REAL, sweep de robustez.

HIPOTESIS: la composicion arcoiris+válvula K/D (calibrada en OTC 60s) es
aplicable a SPOT M15 REAL. Si el gate compuesto no filtra señales operables,
la deuda de dominio (R9) queda NO EVALUADA por insuficiencia, no falsada.

DIAGNOSTICO previo (EURUSD): dir_pass=146448, only_arcoiris=14, only_valvula=0,
BOTH=0. Cuello de botella = válvula K/D (DESVIO=5.0, |K-D| creciente) nunca abre
en M15 real, y arcoiris estricto es casi nulo (14/146k).

Este script hace un SWEEP HONESTO de DESVIO para aislar la variable (metodo
cientifico: cambiar UNA cosa). Reporta WR por config. No se inventa señal:
se reusa build_features/signal_gate de exp_common.py; solo se parametriza DESVIO.

Timing broker aproximado a M15: entry=open[i+1], exit=open[i+2] (entry+~900s).
Etiqueta: "spot M15 REAL, ejecucion simulada (sin cuenta viva)".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "reports" / "CICLO-001"))
from exp_common import build_features, derive_direction, binomial_p  # noqa: E402

FILES = {
    "EURUSD": ROOT / "data" / "strategy_lab" / "cohorte_real_eurusd" / "EURUSD_M15.parquet",
    "XAUUSD": ROOT / "data" / "smc_borrowed" / "XAUUSD_M15.parquet",
}

# Importamos los internos de exp_common para poder variar DESVIO en la valvula.
import exp_common as ec  # noqa: E402


def load_m15(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path).sort_values("time").reset_index(drop=True)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    df["timestamp"] = (pd.to_datetime(df["time"]).astype("int64") // 1_000_000_000).astype(int)
    vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    df["ticks"] = pd.to_numeric(df[vol_col], errors="coerce").fillna(0).astype(int)
    return df


def resolve_m15(feats, i, direction):
    n = len(feats["ts"])
    e_idx, x_idx = i + 1, i + 2
    if e_idx >= n or x_idx >= n:
        return None
    entry = feats["open"][e_idx]
    exit_close = feats["close"][x_idx]
    return (exit_close > entry) if direction == "CALL" else (exit_close < entry)


def run_sweep(asset, path, desvio_vals):
    df = load_m15(path)
    feats, n = build_features(df)
    # precalculamos kd_sep por vela para no recalcular
    out = {}
    for desvio in desvio_vals:
        ec.DESVIO = desvio
        counts = {"CALL": [0, 0], "PUT": [0, 0]}
        for i in range(320, n - 3):
            dr = derive_direction(feats["k"][i], feats["d"][i])
            if dr is None:
                continue
            if not (ec.arcoiris_alineado(feats["close"][i],
                                         [feats[f"ema{p}"][i] for p in ec.EMA_PERIODS], dr)
                    and ec.valvula_abre(feats["k"][i], feats["d"][i],
                                        [abs(feats["k"][j] - feats["d"][j])
                                         for j in range(max(0, i - 3), i + 1)
                                         if not (np.isnan(feats["k"][j]) or np.isnan(feats["d"][j]))],
                                        dr)):
                continue
            res = resolve_m15(feats, i, dr)
            if res is None:
                continue
            counts[dr][0] += 1
            if res:
                counts[dr][1] += 1
        cfg = {}
        for d in ("CALL", "PUT"):
            t, w = counts[d]
            cfg[d] = {"n": t, "w": w,
                      "wr": round(100.0 * w / t, 1) if t else None,
                      "p": binomial_p(w, t, 0.54) if t else 1.0}
        out[f"desvio={desvio}"] = cfg
    return out


if __name__ == "__main__":
    desvio_vals = [1.0, 2.0, 3.0, 5.0]
    results = {}
    for asset, f in FILES.items():
        res = run_sweep(asset, f, desvio_vals)
        results[asset] = res
        print(f"=== {asset} (spot M15 REAL, sweep DESVIO) ===")
        for cfg_name, cfg in res.items():
            line = "  " + cfg_name + " ->"
            for d in ("CALL", "PUT"):
                r = cfg[d]
                line += f" {d}:n={r['n']},WR={r['wr']},p={r['p']:.1e}" if r["n"] else f" {d}:n=0"
            print(line)
    out_dir = ROOT / "reports" / "CICLO-002"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "_raw_results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("\nGuardado en", out_dir / "_raw_results.json")
