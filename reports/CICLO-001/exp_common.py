"""exp_common.py — Módulo común de los experimentos NN/POI del CICLO-001.

Replica fielmente el gate compuesto del EXP-076 (arcoíris 7-EMA + válvula K/D)
sobre velas EURUSD OTC 60s con el timing real del broker:
  - Señal en cierre de vela i (momento t = open_ts[i] + 60)
  - Entry: openPrice de la vela 60s que contiene t+300s (demora broker)
  - Exit:  openPrice de la vela 60s que contiene t+1200s (entry + 900s duración)
  - WIN si close[exit] está del lado del trade.

Funciones puras (numpy/pandas, sin dependencia de src/). Causal: los indicadores
de la vela i usan solo velas <= i.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
CSV = ROOT / "tools" / "quotex-historical-data" / "EURUSD_otc_60s_365days.csv"

# Config congelada EXP-077/EXP-076
EMA_PERIODS = [5, 10, 20, 40, 80, 160, 320]
K_PERIOD = 14
D_PERIOD = 3
SLOW_K = 3
DESVIO = 5.0
STICKY_THRESHOLD = 3.0
EXTREME_LO = 20.0
EXTREME_HI = 80.0
BROKER_DELAY_SEC = 300
DURATION_SEC = 900


# ── Carga ────────────────────────────────────────────────────────────────
def load_otc_60s(path: Path | None = None) -> pd.DataFrame:
    """Carga el CSV OTC 60s; devuelve df con open/high/low/close/ticks y ts (int, seg)."""
    p = path or CSV
    df = pd.read_csv(p)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    df["ticks"] = pd.to_numeric(df["ticks"], errors="coerce").fillna(0).astype(int)
    return df


# ── Estocástico FULL 14,3,3 (fiel al bot) ───────────────────────────────
def compute_stoch_full(highs, lows, closes, k_period=K_PERIOD, d_period=D_PERIOD, slow_k=SLOW_K):
    n = len(closes)
    raw_k = np.full(n, np.nan)
    for i in range(k_period - 1, n):
        hh = max(highs[i - k_period + 1:i + 1])
        ll = min(lows[i - k_period + 1:i + 1])
        raw_k[i] = 50.0 if hh == ll else 100.0 * (closes[i] - ll) / (hh - ll)
    k_list = np.full(n, np.nan)
    for i in range(k_period - 1 + slow_k - 1, n):
        k_list[i] = float(np.nanmean(raw_k[i - slow_k + 1:i + 1]))
    d_list = np.full(n, np.nan)
    for i in range(k_period - 1 + slow_k - 1 + d_period - 1, n):
        d_list[i] = float(np.nanmean(k_list[i - d_period + 1:i + 1]))
    return k_list, d_list


# ── EMAs del arcoíris (x2 progresión) ───────────────────────────────────
def compute_emas(closes, periods=EMA_PERIODS):
    out = []
    for p in periods:
        alpha = 2.0 / (p + 1.0)
        ema = np.empty(len(closes))
        ema[0] = closes[0]
        for t in range(1, len(closes)):
            ema[t] = alpha * closes[t] + (1 - alpha) * ema[t - 1]
        out.append(ema)
    return out


def arcoiris_alineado(close, ema_vals, direction):
    """True si las 7 EMAs están estrictamente apiladas a favor del trade."""
    seq = [close] + list(ema_vals)
    if direction == "CALL":
        return all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
    return all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))


# ── Dirección del Edificio (derive_flags) ───────────────────────────────
def derive_direction(k, d):
    """CALL si sobreventa (k<=20 y d<=20); PUT si sobrecompra (k>=80 y d>=80); None si no."""
    if k is None or d is None or math.isnan(k) or math.isnan(d):
        return None
    if k <= EXTREME_LO and d <= EXTREME_LO:
        return "CALL"
    if k >= EXTREME_HI and d >= EXTREME_HI:
        return "PUT"
    return None


# ── Válvula K/D (gate P3→CONTRATADO de audit_exp_edf) ───────────────────
def valvula_abre(k, d, kd_hist, direction):
    """(a) K salió del extremo en dirección del trade; (b) |K-D| >= DESVIO; (c) |K-D| creciente."""
    if k is None or d is None or math.isnan(k) or math.isnan(d):
        return False
    if direction == "CALL":
        salio = k > EXTREME_LO
    else:
        salio = k < EXTREME_HI
    if not salio:
        return False
    sep = abs(k - d)
    if sep < DESVIO:
        return False
    if len(kd_hist) >= 2:
        if not all(kd_hist[t] <= kd_hist[t + 1] for t in range(len(kd_hist) - 1)):
            return False
    return True


# ── Gate compuesto completo: arcoíris + válvula, por vela ───────────────
def build_features(df: pd.DataFrame):
    """Calcula indicadores por vela. Devuelve dict de arrays numpy alineados al df."""
    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    ts = df["timestamp"].to_numpy(dtype=np.int64)
    n = len(df)
    k, d = compute_stoch_full(h.tolist(), l.tolist(), c.tolist())
    emas = compute_emas(c)
    feats = {
        "open": o, "high": h, "low": l, "close": c, "ts": ts,
        "k": k, "d": d, "kd_sep": np.abs(k - d),
        "ema5": emas[0], "ema10": emas[1], "ema20": emas[2], "ema40": emas[3],
        "ema80": emas[4], "ema160": emas[5], "ema320": emas[6],
        "body": np.abs(c - o), "rng": h - l,
        "body_ratio": np.where((h - l) > 0, np.abs(c - o) / np.maximum(h - l, 1e-12), 0.0),
        "ticks": df["ticks"].to_numpy(dtype=float),
        "ret1": c - np.roll(c, 1), "ret5": c - np.roll(c, 5), "ret20": c - np.roll(c, 20),
    }
    return feats, n


def signal_gate(feats, i, direction, use_arcoiris=True, use_valvula=True, evol_velas=3):
    """Gate compuesto evaluado en la vela i (solo datos <= i)."""
    k, d = feats["k"][i], feats["d"][i]
    if math.isnan(k) or math.isnan(d):
        return False
    # arcoíris
    if use_arcoiris:
        ema_vals = [feats[f"ema{p}"][i] for p in EMA_PERIODS]
        if not arcoiris_alineado(feats["close"][i], ema_vals, direction):
            return False
    # válvula: K salió del extremo + separación creciente
    if use_valvula:
        kd_hist = [abs(feats["k"][j] - feats["d"][j]) for j in range(max(0, i - evol_velas), i + 1)
                   if not (math.isnan(feats["k"][j]) or math.isnan(feats["d"][j]))]
        if not valvula_abre(k, d, kd_hist, direction):
            return False
    return True


def resolve_trade(feats, i, direction, delay_sec=BROKER_DELAY_SEC, dur_sec=DURATION_SEC,
                  señal_en_cierre=True):
    """Timing real del broker sobre velas 60s (velas perfectamente contiguas).

    señal_en_cierre=True : la señal se genera al cierre de la vela i (t = ts[i]+60)
                           -> entry = vela que contiene t+300 (i+6), exit = i+21.
    señal_en_cierre=False: la señal se genera al open (t = ts[i])
                           -> entry = vela que contiene t+300 (i+5), exit = i+20.
    WIN si close[exit] está del lado del trade.
    """
    n = len(feats["ts"])
    t = int(feats["ts"][i]) + (60 if señal_en_cierre else 0)
    t_entry = t + delay_sec
    t_exit = t + delay_sec + dur_sec
    e_idx = i + (delay_sec + (60 if señal_en_cierre else 0)) // 60
    x_idx = i + (delay_sec + dur_sec + (60 if señal_en_cierre else 0)) // 60
    if e_idx >= n or x_idx >= n:
        return None, None, None, None, None, None
    if feats["ts"][e_idx] != t_entry:
        return None, None, None, None, None, None
    if feats["ts"][x_idx] != t_exit:
        return None, None, None, None, None, None
    entry = feats["open"][e_idx]
    exit_close = feats["close"][x_idx]
    win = (exit_close > entry) if direction == "CALL" else (exit_close < entry)
    return win, e_idx, x_idx, entry, feats["open"][x_idx], exit_close


# ── POI (swing_levels_causal, copia fiel de strategy_lab/poi_behavior) ───
def _swings(high, low, k=2):
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


def swing_levels_causal(high, low, min_touches=2, tol_pips=5.0, swing_k=2,
                        lookback=100, pip_size=1e-4):
    """Niveles swing CAUSALES como bandas [lev-tol, lev+tol] con ventana activa.

    Un nivel existe solo en [active_from, active_from + lookback), donde
    active_from = índice del min_touches-ésimo toque (sin futuro).
    Devuelve (floors, ceilings, active_from, active_to).
    """
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    tol = float(tol_pips) * pip_size
    sh_idx, sl_idx = _swings(h, l, k=swing_k)
    swing_prices = np.concatenate([h[sh_idx], l[sl_idx]])
    swing_pos = np.concatenate([sh_idx, sl_idx])
    if swing_prices.size == 0:
        return (np.array([]),) * 4
    levels = np.unique(np.round(swing_prices, 8))
    srt_prices = np.sort(swing_prices)
    lo_idx = np.searchsorted(srt_prices, levels - tol, side="left")
    hi_idx = np.searchsorted(srt_prices, levels + tol, side="right")
    near = hi_idx - lo_idx
    floors, ceilings, act_from, act_to = [], [], [], []
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


def in_poi_band(floors, ceilings, act_from, act_to, i, low, high):
    """True si la vela i está dentro de alguna banda POI activa (semántica poi_zones)."""
    for f, c, a, b in zip(floors, ceilings, act_from, act_to):
        if a <= i < b and low <= c and high >= f:
            return True
    return False


# ── Estadística ──────────────────────────────────────────────────────────
def binomial_p(w, n, p0=0.54):
    """p-valor de una cola (>= w de n con prob p0) vía aproximación normal con corrección de continuidad."""
    if n == 0:
        return 1.0
    mu = n * p0
    sigma = math.sqrt(n * p0 * (1 - p0))
    if sigma == 0:
        return 1.0 if w <= mu else 0.0
    z = (w - 0.5 - mu) / sigma
    return 0.5 * math.erfc(z / math.sqrt(2))


def wr_stats(wins, n, p0=0.54):
    wr = 100.0 * wins / n if n else float("nan")
    return {"n": n, "wins": wins, "wr": round(wr, 1), "p": binomial_p(wins, n, p0)}
