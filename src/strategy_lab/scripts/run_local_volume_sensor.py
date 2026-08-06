"""Sensor volumétrico LOCAL: densidad en el nivel tocado vs densidad local.

Mide solo los últimos N minutos previos al toque del POI y calcula:
- volume_density_at_touch: densidad de ticks en el precio del toque
- local_volume_density: densidad mediana en la ventana local
- hvn_ratio: ratio >1 indica HVN local, <1 indica LVN local

Luego compara hvn_ratio entre rebotes y breaks para ver si separa.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.poi_behavior import DEFAULT_CFG, swing_levels_causal

SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIP = {p: (0.01 if p.endswith("JPY") else 1e-4) for p in PAIRS}

LOCAL_WINDOW = 20  # velas previas al toque
R = 5


class LocalVolumetricSensor:
    def __init__(self, n_bins: int = 120):
        self.n_bins = int(n_bins)

    def _local_edges(self, lo: float, hi: float) -> np.ndarray:
        return np.linspace(float(lo), float(hi), self.n_bins + 1)

    def density_at(self, lows: np.ndarray, highs: np.ndarray, ticks: np.ndarray,
                   touch_price: float) -> float:
        l = np.asarray(lows, float)
        h = np.asarray(highs, float)
        t = np.asarray(ticks, float)
        if l.size == 0:
            return 0.0
        edges = self._local_edges(float(l.min()), float(h.max()))
        prof = np.zeros(self.n_bins, dtype=float)
        for i in range(len(l)):
            lo = int(np.searchsorted(edges, l[i], side="right") - 1)
            hi = int(np.searchsorted(edges, h[i], side="left"))
            lo = max(lo, 0)
            hi = min(hi, self.n_bins - 1)
            if hi < lo:
                continue
            w = t[i] / max(hi - lo + 1, 1)
            prof[lo:hi + 1] += w
        total = float(prof.sum())
        if total <= 0:
            return 0.0
        prof = prof / total
        idx = int(np.searchsorted(edges, touch_price, side="right") - 1)
        idx = max(0, min(idx, self.n_bins - 1))
        return float(prof[idx])

    def local_background(self, lows: np.ndarray, highs: np.ndarray, ticks: np.ndarray) -> float:
        l = np.asarray(lows, float)
        h = np.asarray(highs, float)
        t = np.asarray(ticks, float)
        if l.size == 0:
            return 0.0
        edges = self._local_edges(float(l.min()), float(h.max()))
        prof = np.zeros(self.n_bins, dtype=float)
        for i in range(len(l)):
            lo = int(np.searchsorted(edges, l[i], side="right") - 1)
            hi = int(np.searchsorted(edges, h[i], side="left"))
            lo = max(lo, 0)
            hi = min(hi, self.n_bins - 1)
            if hi < lo:
                continue
            w = t[i] / max(hi - lo + 1, 1)
            prof[lo:hi + 1] += w
        total = float(prof.sum())
        if total <= 0:
            return 0.0
        prof = prof / total
        return float(np.median(prof))


def run_pair(asset: str):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    ticks = pd.to_numeric(df["tick_volume"], errors="coerce").fillna(0).values.astype(float)
    n = len(c)
    if n < 200:
        return {"asset": asset, "error": "short"}

    fl, ce, af, at = swing_levels_causal(h, l, min_touches=2, tol_pips=5.0,
                                          lookback=100, pip_size=PIP[asset])
    active = np.column_stack([af, at])
    prev_c = np.concatenate([[c[0]], c[:-1]])

    sensor = LocalVolumetricSensor()
    reb_ratios = []
    brk_ratios = []
    for i in range(n):
        mask_active = (active[:, 0] <= i) & (i < active[:, 1])
        if not mask_active.any():
            continue
        in_band = (l[i] <= ce[mask_active]) & (h[i] >= fl[mask_active])
        if not in_band.any():
            continue
        k = np.flatnonzero(in_band)[0]
        fl_i = float(fl[mask_active][k])
        ce_i = float(ce[mask_active][k])
        ab = bool(prev_c[i] > ce[mask_active][k])

        start = max(0, i - LOCAL_WINDOW)
        local_l = l[start:i]
        local_h = h[start:i]
        local_t = ticks[start:i]
        if local_l.size == 0:
            continue

        touch_price = float(c[i])
        dens_at = sensor.density_at(local_l, local_h, local_t, touch_price)
        dens_bg = sensor.local_background(local_l, local_h, local_t)
        ratio = dens_at / dens_bg if dens_bg > 0 else 0.0

        seg = slice(i + 1, min(i + R, n - 1) + 1)
        if seg.start >= n:
            continue
        sub_c = c[seg]
        if ab:
            reb = np.flatnonzero(sub_c >= c[i] + DEFAULT_CFG["reb_pips"] * PIP[asset])
            brk = np.flatnonzero(sub_c <= fl_i - DEFAULT_CFG["break_tol"] * PIP[asset])
        else:
            reb = np.flatnonzero(sub_c <= c[i] - DEFAULT_CFG["reb_pips"] * PIP[asset])
            brk = np.flatnonzero(sub_c >= ce_i + DEFAULT_CFG["break_tol"] * PIP[asset])
        if reb.size and (not brk.size or int(reb[0]) <= int(brk[0])):
            reb_ratios.append(ratio)
        elif brk.size:
            brk_ratios.append(ratio)

    reb_arr = np.array(reb_ratios, dtype=float)
    brk_arr = np.array(brk_ratios, dtype=float)
    return {
        "asset": asset,
        "reb_n": int(reb_arr.size),
        "reb_mean": float(reb_arr.mean()) if reb_arr.size else float("nan"),
        "reb_median": float(np.median(reb_arr)) if reb_arr.size else float("nan"),
        "brk_n": int(brk_arr.size),
        "brk_mean": float(brk_arr.mean()) if brk_arr.size else float("nan"),
        "brk_median": float(np.median(brk_arr)) if brk_arr.size else float("nan"),
    }


def main():
    rows = []
    for asset in PAIRS:
        try:
            r = run_pair(asset)
            rows.append(r)
        except Exception as e:
            rows.append({"asset": asset, "error": str(e)})

    cols = ["asset", "reb_n", "reb_mean", "reb_median", "brk_n", "brk_mean", "brk_median"]
    print(",".join(cols))
    for r in rows:
        if "error" in r:
            print(f"{r['asset']},,,,,,ERROR={r['error']}")
            continue
        print(",".join(str(r.get(k, "")) for k in cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
