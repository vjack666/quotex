"""Backtest P1 -> P3 con exclusion de sticky y confirmacion martillo M15.

Reglas documentadas:
- P1: brake candidato.
- P3: espera cruce K/D en extremo CON separacion real.
      No es entrada inmediata: espera hasta que |K-D| >= umbral
      y verifica vela martillo/martillo invertido M15 en direccion del cruce.
      Solo entonces genera entrada.

Salida: eventos por par y winrate excluyendo sticky.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.brake_eval import compute_brake_and_rebote

SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["EURUSD"]
EXTREMES = {"PUT": 80.0, "CALL": 20.0}
STOCH_K = 14
STOCH_D = 3
MIN_CROSS_SEPARATION = 2.0
MAX_LOOKAHEAD = 40  # velas M15 maximas para buscar cruce + confirmacion
R = 5
PIP = {"EURUSD": 1e-4}


def compute_atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    tr1 = h[1:] - l[:-1]
    tr2 = np.abs(h[1:] - c[:-1])
    tr3 = np.abs(l[1:] - c[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.full(len(c), np.nan, dtype=float)
    if len(tr) >= n:
        atr[n] = float(np.mean(tr[:n]))
        for i in range(n + 1, len(c)):
            atr[i] = (atr[i - 1] * (n - 1) + tr[i - 1]) / n
    for i in range(len(atr)):
        if not np.isfinite(atr[i]):
            window = c[max(0, i - 14): i + 1]
            atr[i] = float(np.mean(np.abs(np.diff(window)))) if len(window) > 1 else 0.0
    return atr


def stoch_kd(high: np.ndarray, low: np.ndarray, close: np.ndarray,
             k_period: int = 14, d_period: int = 3) -> tuple[np.ndarray, np.ndarray]:
    low_k = pd.Series(low).rolling(window=k_period, min_periods=k_period).min().values
    high_k = pd.Series(high).rolling(window=k_period, min_periods=k_period).max().values
    denom = high_k - low_k
    k_raw = np.where(denom > 0, 100.0 * (close - low_k) / denom, np.nan)
    k_s = pd.Series(k_raw).rolling(window=3, min_periods=3).mean().values
    k = pd.Series(k_s).rolling(window=d_period, min_periods=d_period).mean().values
    d = pd.Series(k).rolling(window=d_period, min_periods=d_period).mean().values
    return k.astype(float), d.astype(float)


def is_hammer(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    o = np.asarray(open_, float)
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    c = np.asarray(close, float)
    body = np.abs(c - o)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    total = np.maximum(h - l, 1e-9)
    hammer = (lower >= 2 * np.maximum(body, 1e-9)) & (upper <= np.maximum(body, 1e-9)) & (body / total <= 0.3)
    inv = (upper >= 2 * np.maximum(body, 1e-9)) & (lower <= np.maximum(body, 1e-9)) & (body / total <= 0.3)
    return hammer, inv


def simulate(asset: str):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    n = len(c)

    feat = compute_brake_and_rebote(o, h, l, c, {
        "impulse": {"window": 15, "min_pips": 5.0},
        "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
        "rebote": {"fwd": 2, "min_pips": 0.5},
    })
    brake_mask = feat["brake_mask"].astype(bool)
    prev = np.concatenate([np.array([False], dtype=bool), brake_mask[:-1]])
    candidates = np.flatnonzero(brake_mask & (~prev)).tolist()

    k, d = stoch_kd(h, l, c, STOCH_K, STOCH_D)
    hammer, inv_hammer = is_hammer(o, h, l, c)

    records = []
    for i in candidates:
        direction = "CALL" if feat["impulse_net"][i] < 0 else "PUT"
        extreme = EXTREMES[direction]

        # Buscar cruce en extremo con separacion minima
        found_cross = False
        cross_idx = None
        for j in range(i + 1, min(i + MAX_LOOKAHEAD + 1, n - 1)):
            if not (np.isfinite(k[j]) and np.isfinite(d[j]) and np.isfinite(k[j - 1]) and np.isfinite(d[j - 1])):
                continue
            sep = abs(k[j] - d[j])
            if direction == "CALL" and k[j] <= 20 and k[j - 1] <= d[j - 1] and k[j] > d[j] and sep >= MIN_CROSS_SEPARATION:
                found_cross = True
                cross_idx = j
                break
            if direction == "PUT" and k[j] >= 80 and k[j - 1] >= d[j - 1] and k[j] < d[j] and sep >= MIN_CROSS_SEPARATION:
                found_cross = True
                cross_idx = j
                break

        if not found_cross:
            continue

        # Verificar que no es sticky: esperar hasta que |K-D| >= MIN_CROSS_SEPARATION
        # despues del cruce (si vuelve a 0 en las proximas velas, es sticky).
        sticky = False
        confirm_idx = None
        for jj in range(cross_idx + 1, min(cross_idx + 6, n - 1)):
            if not (np.isfinite(k[jj]) and np.isfinite(d[jj]) and np.isfinite(k[jj - 1]) and np.isfinite(d[jj - 1])):
                continue
            sep2 = abs(k[jj] - d[jj])
            if sep2 < MIN_CROSS_SEPARATION:
                sticky = True
                break
            # Si la separacion se mantiene, verificar martillo M15
            if direction == "CALL":
                valid = inv_hammer[jj]
            else:
                valid = hammer[jj]
            if valid:
                confirm_idx = jj
                break

        if sticky or confirm_idx is None:
            continue

        # Desenlace: rebote dentro de R velas tras la confirmacion
        seg = slice(confirm_idx + 1, min(confirm_idx + 1 + R, n - 1) + 1)
        if seg.start >= n:
            continue
        sub_c = c[seg]
        win = False
        if direction == "CALL" and np.any(sub_c >= c[confirm_idx] + 5 * PIP[asset]):
            win = True
        elif direction == "PUT" and np.any(sub_c <= c[confirm_idx] - 5 * PIP[asset]):
            win = True

        records.append({
            "asset": asset,
            "brake_idx": i,
            "cross_idx": cross_idx,
            "confirm_idx": confirm_idx,
            "direction": direction,
            "sticky": sticky,
            "win": win,
            "minutes_brake_to_cross": (cross_idx - i) * 15,
            "minutes_brake_to_entry": (confirm_idx - i) * 15,
        })

    return records


def main():
    records = simulate("EURUSD")
    if not records:
        print("Sin eventos")
        return 0

    df = pd.DataFrame(records)
    print("=== EVENTOS CON ENTRADA (sticky excluido + martillo M15) ===")
    print(f"n={len(df)}, wins={df['win'].sum()}, winrate={df['win'].mean():.3f}")
    print("\n=== TIEMPO FRENO -> ENTRADA ===")
    print(df["minutes_brake_to_entry"].describe())
    print("\n=== DIRECCION ===")
    print(df.groupby("direction").agg(
        total=("win", "count"),
        wins=("win", "sum"),
        winrate=("win", "mean"),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
