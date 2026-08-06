"""Volume Profile — POI por acumulación de ticks en el eje Y (M15).

Determinista y sin I/O: consume arrays OHLC + ticks y devuelve:
- POC
- VA / VAH / VAL por variante A y B
- métricas de grosor
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class VolumePOI:
    asset: str
    poc: float
    vah_a: float
    val_a: float
    vah_b: float
    val_b: float
    ticks_total: int
    grosor_a_pct: float
    grosor_b_pct: float
    grosor_a_pips: float
    grosor_b_pips: float
    hvn_band_touches: int
    lvn_ratio: float


def _build_histogram(
    highs: np.ndarray,
    lows: np.ndarray,
    ticks: np.ndarray,
    band_pct: float = 0.0015,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Histograma por bucket de precio (eje Y).

    - Eje Y: niveles de precio discretizados en celdas de `band_pct`.
    - Eje X implícito: cada vela aporta al bucket su cantidad de ticks.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    t = np.asarray(ticks, dtype=float)

    if h.size == 0 or l.size == 0:
        return np.array([]), np.array([]), 0.0

    price_min = float(np.nanmin(l))
    price_max = float(np.nanmax(h))
    if price_max <= price_min:
        return np.array([]), np.array([]), 0.0

    mid = (price_min + price_max) / 2.0
    rel_band = max(float(band_pct), 1e-12)
    # número de buckets entero para cubrir [min, max] sin saltos finitos
    raw_bins = int(np.ceil((price_max - price_min) / (mid * rel_band))) + 1
    n_bins = max(raw_bins, 4)

    edges = np.linspace(price_min, price_max, n_bins)
    centers = 0.5 * (edges[:-1] + edges[1:])

    hist = np.zeros(centers.size, dtype=float)
    for i in range(h.size):
        t_i = float(t[i])
        if not np.isfinite(t_i) or t_i <= 0:
            continue
        oi = np.searchsorted(edges[1:], l[i], side="left")
        oi = max(0, min(oi, centers.size - 1))
        oj = np.searchsorted(edges[1:], h[i], side="right") - 1
        oi = max(0, min(oi, centers.size - 1))
        oj = max(0, min(oj, centers.size - 1))
        if oj < oi:
            continue
        hist[oi : oj + 1] += t_i / max((oj - oi + 1), 1)

    return centers, hist, mid * rel_band


def _var_a(hist: np.ndarray, centers: np.ndarray, threshold_pct: float = 0.60):
    """Variante A: celdas contiguas >= threshold_pct * POC."""
    if hist.size == 0:
        return None, None, None
    poc = float(centers[int(np.argmax(hist))])
    thr = float(threshold_pct * hist.max())
    mask = hist >= thr
    if not mask.any():
        return poc, poc, poc
    idx = np.flatnonzero(mask)
    lo = int(idx.min())
    hi = int(idx.max())
    return poc, float(centers[hi]), float(centers[lo])


def _var_b(hist: np.ndarray, centers: np.ndarray, coverage: float = 0.70):
    """Variante B: mínimo rango que acumula `coverage` del volumen total."""
    if hist.size == 0:
        return None, None, None
    total = float(hist.sum())
    if total <= 0:
        poc = float(centers[int(np.argmax(hist))])
        return poc, poc, poc
    target = coverage * total
    order = np.argsort(hist)[::-1]
    cum = 0.0
    selected = []
    for j in order:
        selected.append(j)
        cum += float(hist[j])
        if cum >= target:
            break
    lo = int(min(selected))
    hi = int(max(selected))
    poc = float(centers[int(np.argmax(hist))])
    return poc, float(centers[hi]), float(centers[lo])


def _grosor(vah: Optional[float], val: Optional[float], mid: float) -> tuple[float, float]:
    if vah is None or val is None or mid <= 0:
        return 0.0, 0.0
    grosor = max(vah - val, 0.0)
    grosor_pct = grosor / mid
    return grosor, grosor_pct


def build_volume_poi(
    asset: str,
    highs: Sequence[float],
    lows: Sequence[float],
    ticks: Sequence[float],
    band_pct: float = 0.0015,
    threshold_a: float = 0.60,
    coverage_b: float = 0.70,
) -> VolumePOI:
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    t = np.asarray(ticks, dtype=float)
    centers, hist, step = _build_histogram(h, l, t, band_pct=band_pct)
    if centers.size == 0 or hist.size == 0:
        mid = float(np.nanmean(np.asarray(highs))) if len(highs) else 0.0
        return VolumePOI(asset=asset, poc=mid, vah_a=mid, val_a=mid, vah_b=mid, val_b=mid, ticks_total=int(np.nansum(t)), grosor_a_pct=0.0, grosor_b_pct=0.0, grosor_a_pips=0.0, grosor_b_pips=0.0, hvn_band_touches=0, lvn_ratio=1.0)
    poc_a, vah_a, val_a = _var_a(hist, centers, threshold_pct=threshold_a)
    poc_b, vah_b, val_b = _var_b(hist, centers, coverage=coverage_b)
    poc = poc_a if poc_a is not None else poc_b
    mid = float(np.nanmean(np.asarray(highs))) if len(highs) else float(poc or 0.0)
    grosor_a, grosor_a_pct = _grosor(vah_a, val_a, mid)
    grosor_b, grosor_b_pct = _grosor(vah_b, val_b, mid)

    _vah_a = vah_a if vah_a is not None else poc
    _val_a = val_a if val_a is not None else poc
    _vah_b = vah_b if vah_b is not None else poc
    _val_b = val_b if val_b is not None else poc
    hv_lo = min(float(_vah_a), float(_val_a))
    hv_hi = max(float(_vah_a), float(_val_a))
    hv_touches = int(np.sum((l <= hv_hi) & (h >= hv_lo))) if hv_hi >= hv_lo else 0

    # LVN ratio: fracción de buckets bajo el 25% del POC
    thr_lvn = 0.25 * float(hist.max())
    lvn_buckets = int(np.sum(hist > 0)) if hist.max() > 0 else 0
    lvn_ratio = float(np.sum(hist <= thr_lvn)) / max(lvn_buckets, 1)

    return VolumePOI(
        asset=asset,
        poc=float(poc or 0.0),
        vah_a=float(_vah_a),
        val_a=float(_val_a),
        vah_b=float(_vah_b),
        val_b=float(_val_b),
        ticks_total=int(np.nansum(t)),
        grosor_a_pct=float(grosor_a_pct),
        grosor_b_pct=float(grosor_b_pct),
        grosor_a_pips=float(grosor_a),
        grosor_b_pips=float(grosor_b),
        hvn_band_touches=hv_touches,
        lvn_ratio=float(lvn_ratio),
    )
