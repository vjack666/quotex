"""Barrido reducido P1->P3 para winrate alto EURUSD."""
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
R = 5
PIP = {"EURUSD": 1e-4}


def compute_atr(h, l, c, n=14):
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


def stoch_kd(high, low, close, k_period=14, d_period=3):
    low_k = pd.Series(low).rolling(window=k_period, min_periods=k_period).min().values
    high_k = pd.Series(high).rolling(window=k_period, min_periods=k_period).max().values
    denom = high_k - low_k
    k_raw = np.where(denom > 0, 100.0 * (close - low_k) / denom, np.nan)
    k_s = pd.Series(k_raw).rolling(window=3, min_periods=3).mean().values
    k = pd.Series(k_s).rolling(window=d_period, min_periods=d_period).mean().values
    d = pd.Series(k).rolling(window=d_period, min_periods=d_period).mean().values
    return k.astype(float), d.astype(float)


def is_hammer(o, h, l, c, body_max_ratio=0.3):
    o = np.asarray(o, float)
    h = np.asarray(h, float)
    l = np.asarray(l, float)
    c = np.asarray(c, float)
    body = np.abs(c - o)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    total = np.maximum(h - l, 1e-9)
    hammer = (lower >= 2 * np.maximum(body, 1e-9)) & (upper <= np.maximum(body, 1e-9)) & (body / total <= body_max_ratio)
    inv = (upper >= 2 * np.maximum(body, 1e-9)) & (lower <= np.maximum(body, 1e-9)) & (body / total <= body_max_ratio)
    return hammer, inv


def simulate(asset, min_sep, confirm_window, body_max_ratio):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    n = len(c)

    atr_arr = compute_atr(h, l, c)
    feat = compute_brake_and_rebote(o, h, l, c, {
        "impulse": {"window": 15, "min_pips": 5.0},
        "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
        "rebote": {"fwd": 2, "min_pips": 0.5},
    })
    brake_mask = feat["brake_mask"].astype(bool)
    prev = np.concatenate([np.array([False], dtype=bool), brake_mask[:-1]])
    candidates = np.flatnonzero(brake_mask & (~prev)).tolist()

    k, d = stoch_kd(h, l, c, STOCH_K, STOCH_D)
    hammer, inv_hammer = is_hammer(o, h, l, c, body_max_ratio)

    total = 0
    wins = 0
    rejects = 0

    for i in candidates:
        direction = "CALL" if feat["impulse_net"][i] < 0 else "PUT"

        # Cruce en extremo con separacion minima
        found_cross = False
        cross_idx = None
        for j in range(i + 1, min(i + 41, n - 1)):
            if not (np.isfinite(k[j]) and np.isfinite(d[j]) and np.isfinite(k[j - 1]) and np.isfinite(d[j - 1])):
                continue
            sep = abs(k[j] - d[j])
            if direction == "CALL" and k[j] <= 20 and k[j - 1] <= d[j - 1] and k[j] > d[j] and sep >= min_sep:
                found_cross = True
                cross_idx = j
                break
            if direction == "PUT" and k[j] >= 80 and k[j - 1] >= d[j - 1] and k[j] < d[j] and sep >= min_sep:
                found_cross = True
                cross_idx = j
                break

        if not found_cross:
            continue

        # Excluir sticky: la separacion no debe volver a 0 en las proximas velas
        sticky = False
        confirm_idx = None
        for jj in range(cross_idx + 1, min(cross_idx + 1 + confirm_window, n - 1)):
            if not (np.isfinite(k[jj]) and np.isfinite(d[jj]) and np.isfinite(k[jj - 1]) and np.isfinite(d[jj - 1])):
                continue
            sep2 = abs(k[jj] - d[jj])
            if sep2 < min_sep:
                sticky = True
                break
            if direction == "CALL":
                valid = inv_hammer[jj]
            else:
                valid = hammer[jj]
            if valid:
                confirm_idx = jj
                break

        if sticky or confirm_idx is None:
            continue

        seg = slice(confirm_idx + 1, min(confirm_idx + 1 + R, n - 1) + 1)
        if seg.start >= n:
            continue
        sub_c = c[seg]
        total += 1
        if direction == "CALL" and np.any(sub_c >= c[confirm_idx] + 5 * PIP[asset]):
            wins += 1
        elif direction == "PUT" and np.any(sub_c <= c[confirm_idx] - 5 * PIP[asset]):
            wins += 1

    return {"total": total, "wins": wins, "winrate": wins / total if total else 0.0, "rejects": rejects}


def main():
    rows = []
    for min_sep in [1.0, 2.0, 3.0, 4.0, 5.0]:
        for confirm_window in [1, 3, 5, 10]:
            for body_max_ratio in [0.2, 0.3, 0.4]:
                r = simulate("EURUSD", min_sep, confirm_window, body_max_ratio)
                rows.append({**r, "min_sep": min_sep, "confirm_window": confirm_window, "body_max_ratio": body_max_ratio})

    df = pd.DataFrame(rows)
    top = df[df["total"] >= 50].sort_values("winrate", ascending=False).head(20)
    print(top.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
