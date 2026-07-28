"""feature_calc — primitivas de la estrategia de Rubén calculadas desde OHLC M15.

SL-R14: estocástico Full (params en config) como reloj; impulso (recorrido de
cuerpos); freno (achique + alternancia tras el pico, ver LAB-001); POI (zona de
reversión); rebote (reversión N velas tras la señal). Sin wallclock.
(reversión M pips en K velas). Todo determinista, sin reloj de pared.

Funciones puras sobre numpy arrays; los parámetros vienen de la config.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Features:
    stoch_k: np.ndarray          # %K suavizado
    stoch_d: np.ndarray          # %D
    stoch_k_prev: np.ndarray     # %K desplazado `fwd` velas (reloj previo al impulso)
    impulse_net: np.ndarray      # recorrido neto del impulso (close[i]-close[i-L])
    brake_mask: np.ndarray       # True donde el impulso "murió" (freno LAB-001)
    rebote_up: np.ndarray        # True donde hay rebote alcista en fwd velas
    rebote_dn: np.ndarray        # True donde hay rebote bajista en fwd velas


def stochastic_full(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                    k: int = 14, d: int = 3, smooth: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Estocástico Full Lane %K/%D. Devuelve (%K, %D)."""
    high = np.asarray(high, float); low = np.asarray(low, float); close = np.asarray(close, float)
    n = len(close)
    ll = np.full(n, np.nan); hh = np.full(n, np.nan)
    for i in range(k - 1, n):
        ll[i] = low[i - k + 1:i + 1].min()
        hh[i] = high[i - k + 1:i + 1].max()
    rng = hh - ll
    raw = np.where(rng > 0, (close - ll) / rng * 100.0, 50.0)
    kk = _rolling_mean(raw, smooth)
    dd = _rolling_mean(kk, d)
    return kk, dd


def _rolling_mean(x: np.ndarray, w: int) -> np.ndarray:
    """Media móvil simple, rellena con el valor parcial al inicio."""
    out = np.empty_like(x, dtype=float)
    cum = np.cumsum(x)
    for i in range(len(x)):
        lo = max(0, i - w + 1)
        out[i] = (cum[i] - (cum[lo - 1] if lo > 0 else 0.0)) / (i - lo + 1)
    return out


def compute_features(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                     cfg: dict[str, Any]) -> Features:
    """Calcula todas las primitivas de una serie OHLC según cfg."""
    o = np.asarray(open_, float); h = np.asarray(high, float)
    l = np.asarray(low, float); c = np.asarray(close, float)
    n = len(c)

    st = cfg["stochastic"]
    kk, dd = stochastic_full(h, l, c, st["k"], st["d"], st["smooth"])
    fwd_stoch = int(cfg["brake"]["fwd"])   # el reloj previo mira fwd velas atrás
    stoch_k_prev = np.zeros(n)
    stoch_k_prev[fwd_stoch:] = kk[:-fwd_stoch]  # %K desplazado (estado previo al impulso)

    imp = cfg["impulse"]
    L = int(imp["window"])
    min_imp = float(imp["min_pips"]) * 1e-4  # pips -> precio (EURUSD)
    net = np.zeros(n)
    for i in range(L, n):
        net[i] = c[i] - c[i - L]

    br = cfg["brake"]
    fwd = int(br["fwd"])
    max_adv = float(br["max_advance_frac"])
    body = c - o

    brake = np.zeros(n, dtype=bool)
    for i in range(L, n - fwd):
        if abs(net[i]) < min_imp:
            continue
        if net[i] > 0:
            peak = c[i - L:i + 1].max()
            adv = c[i + 1:i + 1 + fwd].max() - peak
        else:
            peak = c[i - L:i + 1].min()
            adv = peak - c[i + 1:i + 1 + fwd].min()
        if adv > max_adv * abs(net[i]):
            continue                      # el impulso continuó: no murió
        if br["require_alternation"]:
            sub = body[i + 1:i + 1 + fwd]
            if not np.any(np.diff(np.sign(sub)) != 0):
                continue                  # sin alternancia de signo
        brake[i] = True

    rb = cfg["rebote"]
    rfwd = int(rb["fwd"])
    min_r = float(rb["min_pips"]) * 1e-4
    reb_up = np.zeros(n, dtype=bool)
    reb_dn = np.zeros(n, dtype=bool)
    for i in range(L, n - rfwd):
        if c[i + rfwd] >= c[i] + min_r:
            reb_up[i] = True
        if c[i + rfwd] <= c[i] - min_r:
            reb_dn[i] = True

    return Features(stoch_k=kk, stoch_d=dd, stoch_k_prev=stoch_k_prev, impulse_net=net,
                    brake_mask=brake, rebote_up=reb_up, rebote_dn=reb_dn)
