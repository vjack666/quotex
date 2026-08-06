"""Backtest P1 -> P2 -> P3 del edificio.

Reproduce las reglas documentadas:
- P1: brake candidato (transicion False->True).
- P2: confirmacion por ratio + body_n como calidad.
- P3: espera de cruce K/D en extremo (>=80 PUT, <=20 CALL) con
      separacion minima y no sticky.
- Confirmacion M15: vela cerrada tras el cruce con martillo/martillo invertido
      en la direccion del cruce.
- Desenlace: tras confirmacion M15, mide si hay rebote dentro de R velas.

Salida: winrate y cantidad de eventos por par, con y sin filtro body_n.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.brake_eval import compute_brake_and_rebote

SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["EURUSD"]  # solo EURUSD por ahora (hay M5)
PIP = {"EURUSD": 1e-4}

BRAKE_CFG = {
    "impulse": {"window": 15, "min_pips": 5.0},
    "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
    "rebote": {"fwd": 2, "min_pips": 0.5},
}
CONFIRM_RATIO = 0.7
BODY_N_THRESHOLD = 0.60
R = 5
EXTREMES = {"PUT": 80.0, "CALL": 20.0}
STOCH_K = 14
STOCH_D = 3
MIN_CROSS_SEPARATION = 2.0  # |K-D| minimo para no sticky
MARTILLO_MAX_BODY_RATIO = 0.3  # cuerpo <= 30% del rango total


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


def is_hammer(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Detecta martillo o martillo invertido en la vela."""
    o = np.asarray(open_, float)
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    c = np.asarray(close, float)
    body = np.abs(c - o)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    total = np.maximum(h - l, 1e-9)
    # martillo: sombra inferior >= 2*body, sombra superior <= body, cuerpo <= 30% rango
    hammer = (lower >= 2 * np.maximum(body, 1e-9)) & (upper <= np.maximum(body, 1e-9)) & (body / total <= MARTILLO_MAX_BODY_RATIO)
    # martillo invertido: sombra superior >= 2*body, sombra inferior <= body, cuerpo <= 30% rango
    inv = (upper >= 2 * np.maximum(body, 1e-9)) & (lower <= np.maximum(body, 1e-9)) & (body / total <= MARTILLO_MAX_BODY_RATIO)
    return hammer, inv


def simulate(asset: str, use_filter: bool):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    n = len(c)

    atr_arr = compute_atr(h, l, c)
    feat = compute_brake_and_rebote(o, h, l, c, BRAKE_CFG)
    brake_mask = feat["brake_mask"].astype(bool)
    prev = np.concatenate([np.array([False], dtype=bool), brake_mask[:-1]])
    candidates = np.flatnonzero(brake_mask & (~prev)).tolist()

    k, d = stoch_kd(h, l, c, STOCH_K, STOCH_D)
    hammer, inv_hammer = is_hammer(o, h, l, c)

    total = 0
    wins = 0
    rejects = 0
    no_cross = 0
    no_separation = 0
    no_hammer = 0

    for i in candidates:
        body = abs(c[i] - o[i])
        norm_atr = float(atr_arr[i]) if np.isfinite(atr_arr[i]) and atr_arr[i] > 0 else 1.0
        body_n = body / norm_atr
        if use_filter and body_n > BODY_N_THRESHOLD:
            rejects += 1
            continue

        direction = "CALL" if feat["impulse_net"][i] < 0 else "PUT"
        extreme = EXTREMES[direction]

        # P3: buscar cruce K/D en extremo con separacion
        found_cross = False
        cross_idx = None
        for j in range(i + 1, min(i + R + 1, n - 1)):
            if not (np.isfinite(k[j]) and np.isfinite(d[j]) and np.isfinite(k[j - 1]) and np.isfinite(d[j - 1])):
                continue
            separation = abs(k[j] - d[j])
            if direction == "CALL" and k[j] <= 20 and k[j - 1] <= d[j - 1] and k[j] > d[j] and separation >= MIN_CROSS_SEPARATION:
                found_cross = True
                cross_idx = j
                break
            if direction == "PUT" and k[j] >= 80 and k[j - 1] >= d[j - 1] and k[j] < d[j] and separation >= MIN_CROSS_SEPARATION:
                found_cross = True
                cross_idx = j
                break

        if not found_cross:
            no_cross += 1
            continue

        # Confirmacion M15: martillo/martillo invertido en la vela cerrada tras el cruce
        conf_idx = cross_idx + 1
        if conf_idx >= n:
            no_hammer += 1
            continue

        if direction == "CALL":
            valid_hammer = inv_hammer[conf_idx]
        else:
            valid_hammer = hammer[conf_idx]

        if not valid_hammer:
            no_hammer += 1
            continue

        # Desenlace: rebote dentro de R velas tras la vela de confirmacion
        seg = slice(conf_idx + 1, min(conf_idx + 1 + R, n - 1) + 1)
        if seg.start >= n:
            continue
        sub_c = c[seg]
        total += 1
        if direction == "CALL" and np.any(sub_c >= c[conf_idx] + 5 * PIP[asset]):
            wins += 1
        elif direction == "PUT" and np.any(sub_c <= c[conf_idx] - 5 * PIP[asset]):
            wins += 1

    return {
        "asset": asset,
        "use_filter": use_filter,
        "total": total,
        "wins": wins,
        "winrate": wins / total if total else 0.0,
        "rejects": rejects,
        "no_cross": no_cross,
        "no_separation": no_separation,
        "no_hammer": no_hammer,
    }


def main():
    print("asset,use_filter,total,wins,winrate,rejects,no_cross,no_separation,no_hammer")
    rows = []
    for asset in PAIRS:
        r_no = simulate(asset, use_filter=False)
        r_yes = simulate(asset, use_filter=True)
        rows.append(r_no)
        rows.append(r_yes)
        print(f"{asset},no,{r_no['total']},{r_no['wins']},{r_no['winrate']:.3f},{r_no['rejects']},{r_no['no_cross']},{r_no['no_separation']},{r_no['no_hammer']}")
        print(f"{asset},yes,{r_yes['total']},{r_yes['wins']},{r_yes['winrate']:.3f},{r_yes['rejects']},{r_yes['no_cross']},{r_yes['no_separation']},{r_yes['no_hammer']}")

    print("\nRESUMEN")
    no_total = sum(r["total"] for r in rows if not r["use_filter"])
    yes_total = sum(r["total"] for r in rows if r["use_filter"])
    no_wins = sum(r["wins"] for r in rows if not r["use_filter"])
    yes_wins = sum(r["wins"] for r in rows if r["use_filter"])
    print(f"Sin filtro: total={no_total}, wins={no_wins}, winrate={no_wins/no_total:.3f}")
    print(f"Con filtro: total={yes_total}, wins={yes_wins}, winrate={yes_wins/yes_total:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
