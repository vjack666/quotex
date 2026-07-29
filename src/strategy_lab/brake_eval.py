"""brake_eval — medición y cálculo vectorizado del edge del freno (muerte del impulso).

Aísla el M2 (Índice de freno): ¿la muerte total del impulso predice el
rebote que sobrevive ~15 min (Ley 6)? Funciones puras sobre numpy arrays,
sin leer datos ni reloj de pared.

El freno alcista = impulso BAJISTA que murió -> espera rebote alcista.
El freno bajista = impulso ALCISTA que murió -> espera rebote bajista.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def _roll_max(x: np.ndarray, w: int) -> np.ndarray:
    """Máximo móvil de ventana w (rellena con el valor parcial al inicio)."""
    if w <= 1:
        return x.copy()
    v = sliding_window_view(x, w)            # shape (n-w+1, w)
    out = np.empty_like(x, dtype=float)
    out[:w - 1] = x[:w - 1]
    out[w - 1:] = v.max(axis=1)
    return out


def _roll_min(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1:
        return x.copy()
    v = sliding_window_view(x, w)
    out = np.empty_like(x, dtype=float)
    out[:w - 1] = x[:w - 1]
    out[w - 1:] = v.min(axis=1)
    return out


def compute_brake_and_rebote(open_: np.ndarray, high: np.ndarray, low: np.ndarray,
                             close: np.ndarray, cfg: dict[str, Any]
                             ) -> dict[str, np.ndarray]:
    """Vectorizado: devuelve brake_mask, rebote_up, rebote_dn según cfg.

    Misma semántica que feature_calc.compute_features (impulse/brake/rebote),
    pero sin loops Python -> ~100x más rápido para barridos.
    """
    o = np.asarray(open_, float); h = np.asarray(high, float)
    l = np.asarray(low, float); c = np.asarray(close, float)
    n = len(c)

    imp = cfg["impulse"]
    L = int(imp["window"])
    min_imp = float(imp["min_pips"]) * 1e-4
    net = np.zeros(n)
    net[L:] = c[L:] - c[:-L]

    br = cfg["brake"]
    fwd = int(br["fwd"])
    max_adv = float(br["max_advance_frac"])
    alt = bool(br["require_alternation"])
    body = c - o

    brake = np.zeros(n, dtype=bool)
    # solo donde hay impulso suficiente
    big = np.abs(net) >= min_imp
    up = net > 0
    dn = net < 0
    # peak del recorrido y avance tras el pico (vectorizado, anclado en i)
    # _roll_max(c, w)[i] = max(c[i-w+1 .. i]); queremos max en [i-L, i] -> w=L+1
    peak_up = _roll_max(c, L + 1)              # max en [i-L, i], len n
    peak_dn = _roll_min(c, L + 1)              # min en [i-L, i], len n
    # avance tras el pico: max/min en [i+1, i+fwd] vs el peak en [i-L, i]
    # (replica feature_calc: c[i+1:i+1+fwd], no incluye i)
    fwd_lo = np.empty_like(c); fwd_lo[:-fwd] = _roll_min(c, fwd)[fwd:]
    fwd_hi = np.empty_like(c); fwd_hi[:-fwd] = _roll_max(c, fwd)[fwd:]
    adv_up_full = fwd_hi - peak_up             # net>0: fwd max vs peak (nuevo max = sigue vivo)
    adv_dn_full = peak_dn - fwd_lo            # net<0: trough vs fwd min (nuevo min = sigue vivo)
    adv = np.full(n, np.inf)
    seg = slice(L, n - fwd)
    adv[seg] = np.where(net[seg] > 0, adv_up_full[seg], adv_dn_full[seg])
    # signed comparison: solo un nuevo extremo mata el brake (coincide con feature_calc)
    brake = big & (adv <= max_adv * np.abs(net))
    if alt:
        # alternancia de signo del cuerpo en [i+1, i+fwd] (coincide con feature_calc)
        # body[i+1:i+1+fwd] con signo -> np.any(np.diff(np.sign(sub)) != 0)
        b = body[1:]                        # length n-1
        if n > fwd:
            win = sliding_window_view(b, fwd)            # (n-fwd, fwd): win[i] = body[i+1:i+1+fwd]
            signs = np.sign(win)
            # diffs[i] = signos cambian entre velas adyacentes dentro de la ventana
            diffs = np.diff(signs, axis=1)               # (n-fwd, fwd-1)
            has_changes = np.any(diffs != 0, axis=1)     # (n-fwd,)
            brake[:n - fwd] = brake[:n - fwd] & has_changes

    rb = cfg["rebote"]
    rfwd = int(rb["fwd"])
    min_r = float(rb["min_pips"]) * 1e-4
    reb_up = np.zeros(n, dtype=bool)
    reb_dn = np.zeros(n, dtype=bool)
    reb_up[L:n - rfwd] = c[L + rfwd:n] >= c[L:n - rfwd] + min_r
    reb_dn[L:n - rfwd] = c[L + rfwd:n] <= c[L:n - rfwd] - min_r

    return {"brake_mask": brake, "impulse_net": net,
            "rebote_up": reb_up, "rebote_dn": reb_dn}


def brake_winrate(feat: dict[str, np.ndarray]) -> dict[str, float]:
    """Edge del freno aislado. feat: brake_mask, impulse_net, rebote_up, rebote_dn."""
    brake = feat["brake_mask"].astype(bool)
    net = feat["impulse_net"]
    up = feat["rebote_up"].astype(bool)
    dn = feat["rebote_dn"].astype(bool)

    br_up = brake & (net < 0)          # impulso bajista frenó -> rebote alcista
    br_dn = brake & (net > 0)          # impulso alcista frenó -> rebote bajista
    n_up = int(br_up.sum()); n_dn = int(br_dn.sum())
    wr_up = float(up[br_up].mean()) if n_up else 0.0
    wr_dn = float(dn[br_dn].mean()) if n_dn else 0.0
    n = n_up + n_dn
    wr = (wr_up * n_up + wr_dn * n_dn) / n if n else 0.0
    return {"n": n, "wr": wr, "n_up": n_up, "wr_up": wr_up,
            "n_dn": n_dn, "wr_dn": wr_dn}
