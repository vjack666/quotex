"""Optimización del ancho de banda del POI por volumen para binarias.

Barre anchos en pips y mide, por par:
- % de velas dentro de la banda
- Número de eventos de brake dentro
- WR del brake dentro/fuera
- Coherencia: signo del delta WR entre pares (más pares en el mismo signo = más coherente)

Sin red neuronal: con 7 pares no hay datos suficientes. Se busca la constante
más coherente, no la óptima individual.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.brake_eval import compute_brake_and_rebote, brake_winrate
from strategy_lab.volume_profile import build_volume_poi


SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIP_SIZE = {p: (0.01 if p.endswith("JPY") else 1e-4) for p in PAIRS}

BRAKE_CFG = {
    "impulse": {"window": 15, "min_pips": 0.5},
    "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
    "rebote": {"fwd": 2, "min_pips": 0.5},
}

BAND_PIPS = np.arange(5, 101, 5)


def _load(asset):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


def run_pair(asset):
    df = _load(asset)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    ticks = df["tick_volume"].values.astype(float)
    ticks = np.where(np.isfinite(ticks), ticks, 0.0)
    n = len(c)

    feat = compute_brake_and_rebote(o, h, l, c, BRAKE_CFG)
    total = brake_winrate(feat)
    if total["n"] == 0:
        return []

    # Baseline: brake fuera del POI por volumen (toda la banda del POC)
    vp0 = build_volume_poi(asset, h, l, ticks)
    band = np.array([min(vp0.val_b, vp0.vah_b), max(vp0.val_b, vp0.vah_b)], dtype=float)
    base_mask = (l <= band[1]) & (h >= band[0])
    base_inside = brake_winrate({"brake_mask": feat["brake_mask"].astype(bool) & base_mask, "impulse_net": feat["impulse_net"], "rebote_up": feat["rebote_up"], "rebote_dn": feat["rebote_dn"]})
    base_outside = brake_winrate({"brake_mask": feat["brake_mask"].astype(bool) & ~base_mask, "impulse_net": feat["impulse_net"], "rebote_up": feat["rebote_up"], "rebote_dn": feat["rebote_dn"]})
    rows = [{
        "asset": asset,
        "band_pips": 0,
        "poc_pct": 0,
        "wr_inside": base_inside["wr"],
        "n_inside": base_inside["n"],
        "wr_outside": base_outside["wr"],
        "n_outside": base_outside["n"],
        "pct_kept": base_inside["n"] / total["n"],
        "delta_wr": base_inside["wr"] - base_outside["wr"],
    }]

    for bp in BAND_PIPS:
        bw = bp * PIP_SIZE[asset]
        vp = build_volume_poi(asset, h, l, ticks, band_pct=bw / max(h.max() - l.min(), 1e-9))
        low_b = min(vp.val_b, vp.vah_b)
        high_b = max(vp.val_b, vp.vah_b)
        mask = (l <= high_b) & (h >= low_b)
        inside = brake_winrate({"brake_mask": feat["brake_mask"].astype(bool) & mask, "impulse_net": feat["impulse_net"], "rebote_up": feat["rebote_up"], "rebote_dn": feat["rebote_dn"]})
        outside = brake_winrate({"brake_mask": feat["brake_mask"].astype(bool) & ~mask, "impulse_net": feat["impulse_net"], "rebote_up": feat["rebote_up"], "rebote_dn": feat["rebote_dn"]})
        poc_frac = (high_b - low_b) / (h.max() - l.min()) if (h.max() - l.min()) > 0 else 0.0
        rows.append({
            "asset": asset,
            "band_pips": int(bp),
            "poc_pct": poc_frac * 100,
            "wr_inside": inside["wr"],
            "n_inside": inside["n"],
            "wr_outside": outside["wr"],
            "n_outside": outside["n"],
            "pct_kept": inside["n"] / total["n"] if total["n"] else 0.0,
            "delta_wr": inside["wr"] - outside["wr"],
        })
    return rows


def main():
    all_rows = []
    for asset in PAIRS:
        all_rows.extend(run_pair(asset))

    # Agregados por ancho: coherencia = % de pares con delta_wr > 0
    summary = []
    for bp in [0] + list(BAND_PIPS):
        sub = [r for r in all_rows if r["band_pips"] == bp]
        if not sub:
            continue
        delta = np.array([r["delta_wr"] for r in sub], dtype=float)
        coh = float(np.mean(delta > 0))
        median_kept = float(np.median([r["pct_kept"] for r in sub]))
        mean_delta = float(delta.mean())
        summary.append({
            "band_pips": bp,
            "coherence": coh,
            "median_kept": median_kept,
            "mean_delta": mean_delta,
            "mean_wr_inside": float(np.mean([r["wr_inside"] for r in sub])),
            "mean_wr_outside": float(np.mean([r["wr_outside"] for r in sub])),
        })

    print("asset,band_pips,poc_pct,wr_inside,wr_outside,delta_wr,pct_kept")
    for r in all_rows:
        print(f"{r['asset']},{r['band_pips']},{r['poc_pct']:.2f},{r['wr_inside']:.3f},{r['wr_outside']:.3f},{r['delta_wr']:.3f},{r['pct_kept']:.3f}")
    print("---SUMMARY---")
    print("band_pips,coherence,median_kept,mean_delta,mean_wr_inside,mean_wr_outside")
    for r in summary:
        print(f"{r['band_pips']},{r['coherence']:.3f},{r['median_kept']:.3f},{r['mean_delta']:.3f},{r['mean_wr_inside']:.3f},{r['mean_wr_outside']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
