"""Barrido POI vs freno sobre los 8 pares M15 prestados (solo análisis, no bot)."""
import time
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from strategy_lab.brake_eval import compute_brake_and_rebote  # noqa: E402
from strategy_lab.poi_filter import poi_zones, brake_within_poi  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BORROWED = ROOT / "data" / "smc_borrowed"
SRC = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
PAIRS = ["EURUSD", "XAUUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
CFG = {"impulse": {"window": 8, "min_pips": 30},
       "brake": {"fwd": 3, "max_advance_frac": 0.10, "require_alternation": True},
       "rebote": {"fwd": 3, "min_pips": 8}}
GRID = [(100, 2, 5.0), (200, 2, 10.0), (100, 3, 10.0)]


def main() -> None:
    t0 = time.perf_counter()
    for lb, mt, tol in GRID:
        agg_f = agg_ft = agg_t = agg_tt = 0.0
        for name in PAIRS:
            local = BORROWED / f"{name}_M15.parquet"
            smc = SRC / f"{name}_M15.parquet"
            p = local if local.exists() else smc
            if not p.exists():
                continue
            df = pd.read_parquet(p).sort_values("time").iloc[-200_000:]
            o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
            feat = compute_brake_and_rebote(o, h, l, c, CFG)
            poi = poi_zones(o, h, l, c, lookback=lb, min_touches=mt, tol_pips=tol)
            r = brake_within_poi(feat, poi)
            agg_f += r["wr_filtrado"] * r["n_filtrado"]; agg_ft += r["n_filtrado"]
            agg_t += r["wr_total"] * r["n_total"]; agg_tt += r["n_total"]
        wr_f = agg_f / agg_ft if agg_ft else 0.0
        wr_t = agg_t / agg_tt if agg_tt else 0.0
        kept = agg_ft / agg_tt if agg_tt else 0.0
        print(f"lb={lb} mt={mt} tol={tol}: WR_filtrado={wr_f:.4f} (n={int(agg_ft)}) "
              f"vs WR_total={wr_t:.4f} (n={int(agg_tt)}) pct_kept={kept:.3f}")
    print(f"[done] {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
