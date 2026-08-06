"""Backtest simulado P1→P2 con brake body_n filter.

Corrige el conteo: solo considera eventos de brake, no cada vela consecutiva.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.brake_eval import compute_brake_and_rebote

SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIP = {p: (0.01 if p.endswith("JPY") else 1e-4) for p in PAIRS}

BRAKE_CFG = {
    "impulse": {"window": 15, "min_pips": 5.0},
    "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
    "rebote": {"fwd": 2, "min_pips": 0.5},
}
BODY_N_THRESHOLD = 0.60


def compute_atr(h, l, c, n=14):
    tr1 = h[1:] - l[:-1]
    tr2 = np.abs(h[1:] - c[:-1])
    tr3 = np.abs(l[1:] - c[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.full(len(c), np.nan)
    if len(tr) >= n:
        atr[n] = np.mean(tr[:n])
        for i in range(n + 1, len(c)):
            atr[i] = (atr[i - 1] * (n - 1) + tr[i - 1]) / n
    for i in range(len(atr)):
        if not np.isfinite(atr[i]):
            window = c[max(0, i - 14): i + 1]
            atr[i] = float(np.mean(np.abs(np.diff(window)))) if len(window) > 1 else 0.0
    return atr


def simulate(asset: str, use_filter: bool):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    n = len(c)

    atr_arr = compute_atr(h, l, c)
    feat = compute_brake_and_rebote(o, h, l, c, BRAKE_CFG)
    brake_mask = feat["brake_mask"].astype(bool)

    # Solo transiciones brake_ok=False -> True = nuevos candidatos
    prev = np.concatenate([[False], brake_mask[:-1]])
    candidates = np.flatnonzero(brake_mask & (~prev)).tolist()

    promotions = 0
    rejections = 0
    body_n_values = []

    for i in candidates:
        body = abs(c[i] - o[i])
        norm_atr = float(atr_arr[i]) if np.isfinite(atr_arr[i]) and atr_arr[i] > 0 else 1.0
        body_n = body / norm_atr
        body_n_values.append(body_n)

        if use_filter and body_n > BODY_N_THRESHOLD:
            rejections += 1
            continue
        promotions += 1

    return {
        "asset": asset,
        "use_filter": use_filter,
        "candidates": int(len(candidates)),
        "promotions": promotions,
        "rejections": rejections,
        "mean_body_n": float(np.mean(body_n_values)) if body_n_values else 0.0,
        "median_body_n": float(np.median(body_n_values)) if body_n_values else 0.0,
        "pct_rejected": float(rejections) / float(len(candidates)) if candidates else 0.0,
    }


def main():
    print("asset,use_filter,candidates,promotions,rejections,mean_body_n,median_body_n,pct_rejected")
    rows = []
    for asset in PAIRS:
        r_no = simulate(asset, use_filter=False)
        r_yes = simulate(asset, use_filter=True)
        rows.append(r_no)
        rows.append(r_yes)
        print(f"{asset},no,{r_no['candidates']},{r_no['promotions']},{r_no['rejections']},{r_no['mean_body_n']:.3f},{r_no['median_body_n']:.3f},{r_no['pct_rejected']:.3f}")
        print(f"{asset},yes,{r_yes['candidates']},{r_yes['promotions']},{r_yes['rejections']},{r_yes['mean_body_n']:.3f},{r_yes['median_body_n']:.3f},{r_yes['pct_rejected']:.3f}")

    print("\nRESUMEN")
    total_no = sum(r["candidates"] for r in rows if not r["use_filter"])
    total_yes = sum(r["candidates"] for r in rows if not r["use_filter"])
    prom_no = sum(r["promotions"] for r in rows if not r["use_filter"])
    prom_yes = sum(r["promotions"] for r in rows if r["use_filter"])
    rej_yes = sum(r["rejections"] for r in rows if r["use_filter"])
    print(f"Total sin filtro: candidates={total_no}, promotions={prom_no}")
    print(f"Total con filtro: candidates={total_yes}, promotions={prom_yes}, rejections={rej_yes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
