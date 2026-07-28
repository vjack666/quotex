"""poi_filter — filtro de contexto POI (M3) para el freno.

Un POI (Point of Interest) es una zona de precio donde el mercado ya
reaccionó antes (swing high/low tocado >= min_touches veces dentro de
una ventana lookback). Hipótesis: operar el freno SOLO dentro de una
zona POI sube el WR o reduce señales elevando calidad.

Puro numpy — sin reloj de pared, sin I/O.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from strategy_lab.brake_eval import brake_winrate

PIP = 1e-4


def _swings(high: np.ndarray, low: np.ndarray, k: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Índices de swing highs / swing lows fractales de orden k."""
    n = len(high)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    for i in range(k, n - k):
        seg_h = high[i - k:i + k + 1]
        seg_l = low[i - k:i + k + 1]
        if high[i] == seg_h.max() and (seg_h == high[i]).sum() == 1:
            sh[i] = True
        if low[i] == seg_l.min() and (seg_l == low[i]).sum() == 1:
            sl[i] = True
    return np.flatnonzero(sh), np.flatnonzero(sl)


def poi_zones(open_: np.ndarray, high: np.ndarray, low: np.ndarray,
              close: np.ndarray, lookback: int = 100, min_touches: int = 2,
              tol_pips: float = 5.0, swing_k: int = 2) -> dict[str, Any]:
    """Marca velas dentro de una zona POI (nivel de swing tocado >= min_touches).

    Determinista y causal: la zona en la vela i solo usa swings en
    [i-lookback, i]. Devuelve dict con 'poi_zone' (bool array len n).
    """
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    n = len(h)
    tol = float(tol_pips) * PIP
    sh_idx, sl_idx = _swings(h, l, k=swing_k)

    # niveles candidatos: precio de cada swing
    levels = np.concatenate([h[sh_idx], l[sl_idx]]) if (len(sh_idx) + len(sl_idx)) else np.empty(0)
    lvl_idx = np.concatenate([sh_idx, sl_idx]) if (len(sh_idx) + len(sl_idx)) else np.empty(0, int)
    order = np.argsort(lvl_idx)
    levels, lvl_idx = levels[order], lvl_idx[order]

    poi = np.zeros(n, dtype=bool)
    swing_prices = np.concatenate([h[sh_idx], l[sl_idx]])
    swing_pos = np.concatenate([sh_idx, sl_idx])

    for j, lev in enumerate(levels):
        i0 = int(lvl_idx[j])
        # toques: otros swings dentro de tol y dentro de lookback hacia atrás/adelante
        near = np.abs(swing_prices - lev) <= tol
        touch_pos = swing_pos[near]
        if len(touch_pos) < min_touches:
            continue
        # el nivel se activa desde el min_touches-ésimo toque (causalidad)
        touch_pos = np.sort(touch_pos)
        active_from = int(touch_pos[min_touches - 1])
        active_to = min(active_from + lookback, n)
        # velas cuyo rango [low, high] toca la banda [lev-tol, lev+tol]
        seg = slice(active_from, active_to)
        hits = (l[seg] <= lev + tol) & (h[seg] >= lev - tol)
        poi[seg] |= hits
    return {"poi_zone": poi}


def brake_within_poi(feat: dict[str, np.ndarray], poi: dict[str, Any],
                     cfg: dict[str, Any] | None = None) -> dict[str, float]:
    """WR del freno restringido a zonas POI vs total.

    feat: salida de compute_brake_and_rebote. poi: salida de poi_zones.
    """
    zone = np.asarray(poi["poi_zone"], bool)
    total = brake_winrate(feat)
    sub = dict(feat)
    sub["brake_mask"] = feat["brake_mask"].astype(bool) & zone
    filt = brake_winrate(sub)
    n_total = int(total["n"])
    pct_kept = (filt["n"] / n_total) if n_total else 0.0
    return {"wr_filtrado": float(filt["wr"]), "n_filtrado": int(filt["n"]),
            "wr_total": float(total["wr"]), "n_total": n_total,
            "pct_kept": float(pct_kept),
            "wr_up_filtrado": float(filt["wr_up"]), "wr_dn_filtrado": float(filt["wr_dn"])}
