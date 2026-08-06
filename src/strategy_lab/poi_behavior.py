"""poi_behavior — comportamiento del POI como soporte/resistencia (fase de freno).

NO mide winrate: eso se mide al final de la cadena de la estrategia
(freno -> K/D -> señal). El POI es el CONTEXTO donde el freno tiene sentido:
un freno sin POI no tiene por qué rebotar; un freno DENTRO de un POI de
calidad sí. Este módulo mide la CALIDAD del POI como nivel:

  H1 — Sostiene el precio: tasa de rebote vs tasa de break en los toques.
  H2 — Timing del freno: cuántas velas tarda el precio (tras tocar el POI)
       en producir un freno REAL (impulso fuerte que muere). Define la espera
       necesaria en la fase 1. Se mide con el detector ESTRICTO de freno.
  H3 — Aguante a caída estrepitosa: tasa de rebote cuando el precio llega con
       impulso fuerte previo vs calma, más el overshoot (cuántos pips hunde
       el POI antes de rebotar).
  H4 — Flip de rol: cuando el POI es atravesado, ¿vuelve a usarse del lado
       contrario? (lo que fue piso puede ser techo y viceversa).

Cada vela cuenta UNA vez: si toca varias bandas, se asigna a la banda cuyo
centro está más cerca del cierre previo (el nivel que el precio está
testeando). Las bandas swing son CAUSALES: un nivel solo existe desde su
2º toque y por `lookback` velas (misma semántica que poi_filter.poi_zones).
Puro numpy, determinista, sin I/O ni reloj de pared.
"""
from __future__ import annotations

from typing import Any

import numpy as np

DEFAULT_CFG = {
    "reb_pips": 5.0,        # pips de rebote para contar "sostuvo"
    "break_tol": 5.0,       # pips más allá del borde para contar "atravesó"
    "R": 5,                 # velas de ventana para rebote/break tras el toque
    "K": 20,                # velas para buscar el primer freno real tras el toque
    "Q": 10,                # velas para buscar retest tras un break
    "imp_window": 15,       # velas del impulso previo (misma que brake_eval)
    "strong_pct": 75.0,     # percentil |impulso| que define "caída estrepitosa"
}


def va_band_windowed(low: np.ndarray, high: np.ndarray, ticks: np.ndarray,
                     pip_size: float, band_pips: float, coverage: float = 0.70,
                     variant: str = "B") -> tuple[float, float] | None:
    """Franja de volumen sobre un segmento de velas (bins en PIPS, no %).

    Histograma de ticks por bin de `band_pips` sobre [low.min, high.max] del
    segmento. Variante A: celdas contiguas >= 60% del POC. Variante B (VA
    estándar): mínimo rango que acumula `coverage` del volumen total.
    Devuelve (floor, ceiling) o None si no hay datos válidos.
    """
    l = np.asarray(low, float)
    h = np.asarray(high, float)
    t = np.asarray(ticks, float)
    if l.size == 0:
        return None
    pmin = float(l.min()); pmax = float(h.max())
    if pmax <= pmin:
        return None
    bw = float(band_pips) * pip_size
    n_bins = max(int(np.ceil((pmax - pmin) / bw)), 4)
    edges = np.linspace(pmin, pmax, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])

    lo = np.searchsorted(edges, l, side="right") - 1
    hi = np.searchsorted(edges, h, side="left")
    lo = np.clip(lo, 0, n_bins - 1)
    hi = np.clip(hi, 0, n_bins - 1)
    val = t / np.maximum(hi - lo + 1, 1)

    c_lo = np.bincount(lo, weights=val, minlength=n_bins + 1)
    c_hi = np.bincount(np.minimum(hi + 1, n_bins), weights=-val, minlength=n_bins + 1)
    hist = np.cumsum(c_lo + c_hi)[:n_bins]
    total = float(hist.sum())
    if total <= 0:
        return None
    poc = int(np.argmax(hist))
    if variant == "A":
        thr = 0.60 * hist.max()
        mask = hist >= thr
        if not mask.any():
            return float(centers[poc]), float(centers[poc])
        j0, j1 = int(np.flatnonzero(mask).min()), int(np.flatnonzero(mask).max())
        return float(centers[j0]), float(centers[j1])
    # variante B: VA — mínimo rango con `coverage` del volumen
    order = np.argsort(hist)[::-1]
    cum = 0.0
    selected: list[int] = []
    for j in order:
        selected.append(int(j))
        cum += float(hist[j])
        if cum >= coverage * total:
            break
    j0, j1 = min(selected), max(selected)
    return float(centers[j0]), float(centers[j1])


def _desenlace(c: np.ndarray, l: np.ndarray, h: np.ndarray, i: int,
               fl: float, ce: float, ab: bool, reb: float, bt: float, R: int,
               n: int) -> tuple[str, int]:
    """Desenlace de un toque en i contra la banda [fl, ce]. → (outcome, brk_pos)."""
    seg = slice(i + 1, min(i + R, n - 1) + 1)
    if seg.start >= n:
        return "neutro", -1
    sub_c = c[seg]
    if ab:
        reb_at = np.flatnonzero(sub_c >= c[i] + reb)
        brk_at = np.flatnonzero(sub_c <= fl - bt)
    else:
        reb_at = np.flatnonzero(sub_c <= c[i] - reb)
        brk_at = np.flatnonzero(sub_c >= ce + bt)
    ia = int(reb_at[0]) if reb_at.size else -1
    ib = int(brk_at[0]) if brk_at.size else -1
    if ia != -1 and (ib == -1 or ia <= ib):
        return "rebote", -1
    if ib != -1:
        return "break", i + 1 + ib
    return "neutro", -1


def swing_levels_causal(high: np.ndarray, low: np.ndarray, min_touches: int = 2,
                        tol_pips: float = 5.0, swing_k: int = 2,
                        lookback: int = 100, pip_size: float = 1e-4
                        ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Niveles swing CAUSALES como bandas [lev-tol, lev+tol] con ventana activa.

    Un nivel existe solo en [active_from, active_from + lookback), donde
    active_from = índice del min_touches-ésimo toque del nivel (sin futuro).
    Devuelve (floors, ceilings, active_from, active_to).
    """
    from strategy_lab.poi_filter import _swings
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    tol = float(tol_pips) * pip_size
    sh_idx, sl_idx = _swings(h, l, k=swing_k)
    swing_prices = np.concatenate([h[sh_idx], l[sl_idx]])
    swing_pos = np.concatenate([sh_idx, sl_idx])
    if swing_prices.size == 0:
        return (np.array([]),) * 4

    # niveles únicos (dedupe por precio redondeado)
    levels = np.unique(np.round(swing_prices, 8))
    srt_prices = np.sort(swing_prices)
    lo_idx = np.searchsorted(srt_prices, levels - tol, side="left")
    hi_idx = np.searchsorted(srt_prices, levels + tol, side="right")
    near = hi_idx - lo_idx

    floors: list[float] = []
    ceilings: list[float] = []
    act_from: list[int] = []
    act_to: list[int] = []
    for k_, lev in enumerate(levels):
        if near[k_] < min_touches:
            continue
        in_band = np.abs(swing_prices - lev) <= tol
        pos = np.sort(swing_pos[in_band])
        if pos.size < min_touches:
            continue
        if not (np.diff(pos) <= lookback).any():
            continue
        a0 = int(pos[min_touches - 1])
        floors.append(float(lev - tol))
        ceilings.append(float(lev + tol))
        act_from.append(a0)
        act_to.append(min(a0 + lookback, int(len(h))))
    if not floors:
        return (np.array([]),) * 4
    return (np.array(floors), np.array(ceilings),
            np.array(act_from, int), np.array(act_to, int))


def analyze_levels(
    low: np.ndarray, high: np.ndarray, close: np.ndarray,
    floors: np.ndarray, ceilings: np.ndarray,
    active_from: np.ndarray, active_to: np.ndarray,
    brake_strict: np.ndarray, impulse_prev: np.ndarray, strong_thr: float,
    cfg: dict[str, Any] | None = None, pip_size: float = 1e-4,
) -> dict[str, float]:
    """Métricas de comportamiento para un conjunto de bandas POI.

    low/high/close: arrays M15 del par. floors/ceilings: bandas.
    active_from/active_to: ventanas de vigencia por banda (para el swing
    causal; para volumen: 0 y n). brake_strict: eventos de freno REAL
    (impulso fuerte que muere, detector estricto) — usado para el timing H2.
    impulse_prev[i] = c[i] - c[i-L]. strong_thr: umbral |impulso| para
    separar llegada fuerte (caída estrepitosa) de débil.
    """
    c = np.asarray(close, float)
    l = np.asarray(low, float)
    h = np.asarray(high, float)
    n = len(c)
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    reb = float(cfg["reb_pips"]) * pip_size
    bt = float(cfg["break_tol"]) * pip_size
    R = int(cfg["R"]); K = int(cfg["K"]); Q = int(cfg["Q"])

    if n < 30 or floors.size == 0:
        return {"error": "no_bands"}

    floors = np.asarray(floors, float)
    ceilings = np.asarray(ceilings, float)
    active_from = np.asarray(active_from, int)
    active_to = np.asarray(active_to, int)
    centers = 0.5 * (floors + ceilings)
    prev_c = np.concatenate([[c[0]], c[:-1]])

    # ---- Toques por nivel en su ventana activa ----
    all_v: list[np.ndarray] = []
    all_l: list[np.ndarray] = []
    for k_ in range(floors.size):
        a, b = int(active_from[k_]), int(active_to[k_])
        if a >= b:
            continue
        seg = slice(a, b)
        hit = np.flatnonzero((l[seg] <= ceilings[k_]) & (h[seg] >= floors[k_]))
        if hit.size:
            all_v.append(hit + a)
            all_l.append(np.full(hit.size, k_, int))
    if not all_v:
        return {"error": "no_touches"}
    tv = np.concatenate(all_v)
    tl = np.concatenate(all_l)

    # Solo toques direccionales (el precio viene de fuera de la banda)
    pc = prev_c[tv]
    dirs = (pc > ceilings[tl]) | (pc < floors[tl])
    tv, tl = tv[dirs], tl[dirs]
    if tv.size == 0:
        return {"error": "no_directional"}

    # ---- Asignar cada vela a UN nivel (el más cercano al cierre previo) ----
    dist = np.abs(prev_c[tv] - centers[tl])
    idx = np.lexsort((dist, tv))
    tv, tl, dist = tv[idx], tl[idx], dist[idx]
    uniq_v, first = np.unique(tv, return_index=True)
    tv, tl = uniq_v, tl[first]
    ab_flags = prev_c[tv] > ceilings[tl]          # True: viene de arriba (POI=piso)

    n_touches = int(tv.size)
    rebounds = breaks = neutros = 0
    timing: list[int] = []
    h3 = {"fuerte": [0, 0], "debil": [0, 0]}      # [toques, rebotes]
    overshoot = {"fuerte": [], "debil": []}
    flip_breaks = flip_retests = flip_flips = 0

    for pos, i in enumerate(tv):
        k_ = int(tl[pos])
        fl = floors[k_]; ce = ceilings[k_]
        ab = bool(ab_flags[pos])
        seg = slice(i + 1, min(i + R, n - 1) + 1)
        has_seg = seg.start < n

        # ---- H1: desenlace ----
        outcome = "neutro"
        if has_seg:
            sub_c = c[seg]
            if ab:
                reb_at = np.flatnonzero(sub_c >= c[i] + reb)
                brk_at = np.flatnonzero(sub_c <= fl - bt)
            else:
                reb_at = np.flatnonzero(sub_c <= c[i] - reb)
                brk_at = np.flatnonzero(sub_c >= ce + bt)
            ia = int(reb_at[0]) if reb_at.size else -1
            ib = int(brk_at[0]) if brk_at.size else -1
            if ia != -1 and (ib == -1 or ia <= ib):
                outcome = "rebote"
            elif ib != -1:
                outcome = "break"
        if outcome == "rebote":
            rebounds += 1
        elif outcome == "break":
            breaks += 1
        else:
            neutros += 1

        # ---- H2: velas hasta el primer freno REAL tras el toque ----
        seg_k = slice(i, min(i + K, n - 1) + 1)
        hit = np.flatnonzero(brake_strict[seg_k])
        if hit.size:
            timing.append(int(hit[0]))

        # ---- H3: clasificación por impulso previo + overshoot ----
        strong = abs(float(impulse_prev[i])) >= strong_thr
        bucket = "fuerte" if strong else "debil"
        h3[bucket][0] += 1
        if outcome == "rebote" and has_seg:
            h3[bucket][1] += 1
            if ab:
                overshoot[bucket].append(max(0.0, fl - float(l[i + 1:i + R + 1].min())))
            else:
                overshoot[bucket].append(max(0.0, float(h[i + 1:i + R + 1].max()) - ce))

        # ---- H4: flip de rol tras un break ----
        if outcome == "break" and has_seg:
            if ab:
                brk_off = int(np.flatnonzero(c[i + 1:i + R + 1] <= fl - bt)[0])
            else:
                brk_off = int(np.flatnonzero(c[i + 1:i + R + 1] >= ce + bt)[0])
            brk_pos = i + 1 + brk_off
            end = min(brk_pos + 1 + Q, n)
            if end > brk_pos + 1:
                seg_r = slice(brk_pos + 1, end)
                prev_r = np.concatenate([[c[brk_pos]], c[brk_pos + 1:end - 1]])
                if ab:  # break bajista: retest tocando la banda desde abajo
                    ret = np.flatnonzero(
                        (l[seg_r] <= ce + bt) & (h[seg_r] >= fl - bt) & (prev_r < fl)
                    )
                    if ret.size:
                        flip_retests += 1
                        j = brk_pos + 1 + int(ret[0])
                        if (c[j + 1:j + 1 + R] <= c[j] - reb).any():
                            flip_flips += 1
                else:   # break alcista: retest tocando la banda desde arriba
                    ret = np.flatnonzero(
                        (l[seg_r] <= ce + bt) & (h[seg_r] >= fl - bt) & (prev_r > ce)
                    )
                    if ret.size:
                        flip_retests += 1
                        j = brk_pos + 1 + int(ret[0])
                        if (c[j + 1:j + 1 + R] >= c[j] + reb).any():
                            flip_flips += 1
            flip_breaks += 1

    timing_arr = np.asarray(timing, float)
    out = {
        "touches": float(n_touches),
        "rebounds": float(rebounds),
        "breaks": float(breaks),
        "neutros": float(neutros),
        "rate_rebound": rebounds / n_touches if n_touches else 0.0,
        "rate_break": breaks / n_touches if n_touches else 0.0,
        "timing_n": float(timing_arr.size),
        "timing_median": float(np.median(timing_arr)) if timing_arr.size else float("nan"),
        "timing_pct_le1": float((timing_arr <= 1).mean()) if timing_arr.size else float("nan"),
        "timing_pct_le3": float((timing_arr <= 3).mean()) if timing_arr.size else float("nan"),
        "timing_pct_le5": float((timing_arr <= 5).mean()) if timing_arr.size else float("nan"),
        "fuerte_n": float(h3["fuerte"][0]),
        "fuerte_rate": h3["fuerte"][1] / h3["fuerte"][0] if h3["fuerte"][0] else float("nan"),
        "debil_n": float(h3["debil"][0]),
        "debil_rate": h3["debil"][1] / h3["debil"][0] if h3["debil"][0] else float("nan"),
        "overshoot_fuerte": float(np.mean(overshoot["fuerte"]) / pip_size) if overshoot["fuerte"] else float("nan"),
        "overshoot_debil": float(np.mean(overshoot["debil"]) / pip_size) if overshoot["debil"] else float("nan"),
        "flip_breaks": float(flip_breaks),
        "flip_retests": float(flip_retests),
        "flip_flips": float(flip_flips),
        "flip_rate": flip_flips / flip_breaks if flip_breaks else float("nan"),
        "n_bands": float(floors.size),
    }
    return out
