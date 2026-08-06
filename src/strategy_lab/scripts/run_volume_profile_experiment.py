"""Runner del experimento POI volumen vs POI actual (swing).

Solo lectura sobre parquet de SMC-SYSTEMS. No toca el edificio.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import pandas as pd
except Exception:
    pd = None

from strategy_lab.volume_profile import build_volume_poi
from strategy_lab.poi_filter import poi_zones
from strategy_lab.brake_eval import compute_brake_and_rebote, brake_winrate


SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = [
    "AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
]

BRAKE_CFG = {
    "impulse": {"window": 15, "min_pips": 0.5},
    "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
    "rebote": {"fwd": 2, "min_pips": 0.5},
}


def _load_m15(asset: str) -> pd.DataFrame:
    path = SMC_ROOT / f"{asset}_M15.parquet"
    if pd is None:
        raise RuntimeError("pandas requerido")
    df = pd.read_parquet(path)
    df = df.rename(columns={"tick_volume": "ticks"})
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


def _metrics_for_mask(feat: dict[str, np.ndarray], mask: np.ndarray) -> dict[str, float]:
    total = brake_winrate(feat)
    sub = dict(feat)
    sub["brake_mask"] = feat["brake_mask"].astype(bool) & mask.astype(bool)
    filt = brake_winrate(sub)
    return {
        "wr_total": float(total["wr"]),
        "n_total": float(total["n"]),
        "wr_filtrado": float(filt["wr"]),
        "n_filtrado": float(filt["n"]),
        "pct_kept": float(filt["n"] / total["n"]) if total["n"] else 0.0,
    }


def run_pair(asset: str, window: int = 100, min_touches: int = 2, tol_pips: float = 5.0) -> dict[str, object]:
    df = _load_m15(asset)
    if len(df) < window + 30:
        return {"asset": asset, "error": "short"}

    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    ticks = df["ticks"].values.astype(float)
    ticks = np.where(np.isfinite(ticks), ticks, 0.0)

    feat = compute_brake_and_rebote(o, h, l, c, BRAKE_CFG)
    total = brake_winrate(feat)
    if total["n"] == 0:
        return {"asset": asset, "error": "no_brake_events", "n_total": 0}

    poi_swing = poi_zones(o, h, l, c, lookback=window, min_touches=min_touches, tol_pips=tol_pips)
    swing = _metrics_for_mask(feat, poi_swing["poi_zone"])

    vp = build_volume_poi(asset, h, l, ticks, band_pct=0.0015, threshold_a=0.60, coverage_b=0.70)
    mid = (h.max() + h.min()) / 2.0 if h.size else float(vp.poc)
    if mid <= 0:
        mid = float(vp.poc) if vp.poc > 0 else 1.0
    vah_a = max(vp.vah_a, vp.val_a)
    val_a = min(vp.vah_a, vp.val_a)
    vp_mask_a = np.array((l <= vah_a) & (h >= val_a), dtype=bool) if vah_a >= val_a else np.zeros(len(df), dtype=bool)
    vol_a = _metrics_for_mask(feat, vp_mask_a)

    vah_b = max(vp.vah_b, vp.val_b)
    val_b = min(vp.vah_b, vp.val_b)
    vp_mask_b = np.array((l <= vah_b) & (h >= val_b), dtype=bool) if vah_b >= val_b else np.zeros(len(df), dtype=bool)
    vol_b = _metrics_for_mask(feat, vp_mask_b)

    return {
        "asset": asset,
        "rows": int(len(df)),
        "n_total": int(total["n"]),
        "swing_wr": swing["wr_filtrado"],
        "swing_n": int(swing["n_filtrado"]),
        "swing_pct_kept": swing["pct_kept"],
        "vol_a_wr": vol_a["wr_filtrado"],
        "vol_a_n": int(vol_a["n_filtrado"]),
        "vol_a_pct_kept": vol_a["pct_kept"],
        "vol_b_wr": vol_b["wr_filtrado"],
        "vol_b_n": int(vol_b["n_filtrado"]),
        "vol_b_pct_kept": vol_b["pct_kept"],
        "vp_poc": round(vp.poc, 5),
        "vp_val_a": round(vp.val_a, 5),
        "vp_vah_a": round(vp.vah_a, 5),
        "vp_val_b": round(vp.val_b, 5),
        "vp_vah_b": round(vp.vah_b, 5),
        "vp_grosor_a_pct": round(vp.grosor_a_pct, 5),
        "vp_grosor_b_pct": round(vp.grosor_b_pct, 5),
        "vp_ticks_total": int(vp.ticks_total),
        "vp_hvn_touches": int(vp.hvn_band_touches),
        "vp_lvn_ratio": round(vp.lvn_ratio, 3),
    }


def main() -> int:
    results = []
    for asset in PAIRS:
        try:
            r = run_pair(asset)
            results.append(r)
        except Exception as e:
            results.append({"asset": asset, "error": str(e)})

    print("asset,rows,n_total,swing_wr,swing_n,swing_pct_kept,vol_a_wr,vol_a_n,vol_a_pct_kept,vol_b_wr,vol_b_n,vol_b_pct_kept,vp_poc,vp_val_a,vp_vah_a,vp_val_b,vp_vah_b,vp_grosor_a_pct,vp_grosor_b_pct,vp_ticks_total,vp_hvn_touches,vp_lvn_ratio")
    for r in results:
        if "error" in r:
            print(f"{r['asset']},,,,,,,,,,,,,,,,,,,,,ERROR={r['error']}")
            continue
        line = (
            f"{r['asset']},"
            f"{r['rows']},"
            f"{r['n_total']},"
            f"{r['swing_wr']:.3f},{r['swing_n']},{r['swing_pct_kept']:.3f},"
            f"{r['vol_a_wr']:.3f},{r['vol_a_n']},{r['vol_a_pct_kept']:.3f},"
            f"{r['vol_b_wr']:.3f},{r['vol_b_n']},{r['vol_b_pct_kept']:.3f},"
            f"{r['vp_poc']},{r['vp_val_a']},{r['vp_vah_a']},{r['vp_val_b']},{r['vp_vah_b']},"
            f"{r['vp_grosor_a_pct']},{r['vp_grosor_b_pct']},"
            f"{r['vp_ticks_total']},{r['vp_hvn_touches']},{r['vp_lvn_ratio']:.3f}"
        )
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
