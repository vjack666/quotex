"""Features por vela para el pipeline Edificio (laboratorio IA).

Regla clave: todo cálculo es causal, sin look-ahead.
Solo usa datos hasta el índice actual.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from strategy_lab.brake_eval import compute_brake_and_rebote


SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")

PIP_FACTOR = {
    "EURUSD": 1e-4,
    "GBPUSD": 1e-4,
    "AUDUSD": 1e-4,
    "NZDUSD": 1e-4,
    "USDCAD": 1e-4,
    "USDCHF": 1e-4,
    "USDJPY": 1e-2,
}


def load_m15(asset: str, root: Path = SMC_ROOT) -> pd.DataFrame:
    path = root / f"{asset}_M15.parquet"
    df = pd.read_parquet(path)
    df = df[["time", "open", "high", "low", "close", "tick_volume"]].dropna().reset_index(drop=True)
    return df


def load_htf(asset: str, root: Path = SMC_ROOT, tf: str = "H4") -> Optional[pd.DataFrame]:
    path = root / f"{asset}_{tf}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df = df[["time", "close"]].dropna().reset_index(drop=True)
    df = df.rename(columns={"close": f"close_{tf}"})
    return df


def align_htf(df_m15: pd.DataFrame, df_htf: Optional[pd.DataFrame], tf_label: str = "H4") -> pd.Series:
    if df_htf is None:
        return pd.Series(np.nan, index=df_m15.index, dtype=float)

    htf = df_htf.copy()
    htf = htf.sort_values("time")
    htf_col = f"close_{tf_label}"

    m15_time = pd.to_datetime(df_m15["time"], utc=True).astype("datetime64[ns, UTC]")
    htf_time = pd.to_datetime(htf["time"], utc=True).astype("datetime64[ns, UTC]")

    left = pd.DataFrame({"time": m15_time.sort_values().values})
    right = pd.DataFrame({
        "htf_time": htf_time.values,
        htf_col: htf[htf_col].astype(float).values,
    })
    merged = pd.merge_asof(
        left,
        right,
        left_on="time",
        right_on="htf_time",
        direction="backward",
    )
    bias = merged[htf_col]
    bias.index = df_m15.index
    bias = bias.astype(float)
    bias = bias / bias.rolling(20, min_periods=10).mean() - 1.0
    return bias


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


def compute_kd(high: np.ndarray, low: np.ndarray, close: np.ndarray,
               k_period: int = 14, d_period: int = 3) -> tuple[np.ndarray, np.ndarray]:
    low_k = pd.Series(low).rolling(window=k_period, min_periods=k_period).min().values
    high_k = pd.Series(high).rolling(window=k_period, min_periods=k_period).max().values
    denom = high_k - low_k
    k_raw = np.where(denom > 0, 100.0 * (close - low_k) / denom, np.nan)
    k_s = pd.Series(k_raw).rolling(window=3, min_periods=3).mean().values
    k = pd.Series(k_s).rolling(window=d_period, min_periods=d_period).mean().values
    d = pd.Series(k).rolling(window=d_period, min_periods=d_period).mean().values
    return k.astype(float), d.astype(float)


def _cross_flags(k: np.ndarray, d: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(k)
    cross = np.full(n, None, dtype=object)
    cross_ago = np.full(n, np.nan)
    cruce_en_zona = np.full(n, False, dtype=bool)

    last_cross_idx: Optional[int] = None
    for i in range(1, n):
        if not (np.isfinite(k[i]) and np.isfinite(d[i]) and np.isfinite(k[i - 1]) and np.isfinite(d[i - 1])):
            continue
        if k[i - 1] <= d[i - 1] and k[i] > d[i]:
            last_cross_idx = i
            cross[i] = "alcista"
            cross_ago[i] = 0
            cruce_en_zona[i] = bool(k[i] <= 20)
        elif k[i - 1] >= d[i - 1] and k[i] < d[i]:
            last_cross_idx = i
            cross[i] = "bajista"
            cross_ago[i] = 0
            cruce_en_zona[i] = bool(k[i] >= 80)

    if last_cross_idx is not None:
        for j in range(last_cross_idx + 1, n):
            if np.isfinite(cross_ago[j]):
                continue
            cross_ago[j] = j - last_cross_idx

    return cross, cross_ago, cruce_en_zona


def detect_hammer(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                  body_max_ratio: float = 0.3) -> tuple[np.ndarray, np.ndarray]:
    o = np.asarray(open_, float)
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    c = np.asarray(close, float)
    body = np.abs(c - o)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    total = np.maximum(h - l, 1e-9)
    hammer = (lower >= 2 * np.maximum(body, 1e-9)) & (upper <= np.maximum(body, 1e-9)) & (body / total <= body_max_ratio)
    inv = (upper >= 2 * np.maximum(body, 1e-9)) & (lower <= np.maximum(body, 1e-9)) & (body / total <= body_max_ratio)
    return hammer.astype(bool), inv.astype(bool)


def build_feature_frame(df: pd.DataFrame, df_htf: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    v = df["tick_volume"].values.astype(float)

    body = np.abs(c - o)
    range_ = np.maximum(h - l, 1e-9)
    body_ratio = body / range_
    range_pct = range_ / np.maximum(c, 1e-9)

    atr = compute_atr(h, l, c)
    body_n = body / np.maximum(atr, 1e-9)

    feat = compute_brake_and_rebote(o, h, l, c, {
        "impulse": {"window": 15, "min_pips": 5.0},
        "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
        "rebote": {"fwd": 2, "min_pips": 0.5},
    })
    brake_mask = feat["brake_mask"].astype(bool)
    impulse_net = feat["impulse_net"].astype(float)
    prev_brake = np.concatenate([np.array([False]), brake_mask[:-1]])
    brake_transition = (brake_mask & ~prev_brake).astype(bool)

    k, d = compute_kd(h, l, c)
    kd_dist = np.abs(k - d)

    hammer, inv_hammer = detect_hammer(o, h, l, c)

    rvol = v / np.maximum(pd.Series(v).rolling(20, min_periods=10).mean().values, 1e-9)

    trend = pd.Series(c).rolling(10, min_periods=2).apply(
        lambda x: float(np.polyfit(np.arange(len(x)), x, 1)[0]) if len(x) >= 2 else np.nan, raw=True
    ).values / np.maximum(c, 1e-9)

    range_ref = pd.Series(range_).rolling(15, min_periods=5).mean().values
    brake_ratio = range_ / np.maximum(range_ref, 1e-9)

    try:
        htf_bias = align_htf(df, df_htf).values
    except Exception as exc:
        print(f"[warn] align_htf failed: {exc}; htf_bias=NaN")
        htf_bias = np.full(len(df), np.nan, dtype=float)

    n = len(df)
    n = len(df)
    split_mask = np.full(n, "train", dtype=object)
    train_end = int(n * 0.70)
    split_mask[train_end:] = "test"
    cross, cross_ago, cruce_en_zona = _cross_flags(k, d)

    # ── Confirmaciones CAUSALES ──
    # Regla dura: una confirmación en la vela i sólo usa datos hasta i (velas
    # cerradas). Nada de i+1 / i+2: eso es look-ahead y contamina el dataset.
    # El "freno confirmado" = freno en i + continuación visible EN i:
    #   - el rango de i está en contracción vs la vela previa (el impulso se frenó), y
    #   - el contexto ya está en zona de interés (cruce_en_zona o cruce reciente).
    # El "cruce limpio" = en i el estocástico ya está fuera de zona muerta y con
    #   separación K/D suficiente (estado observable, no predicho).
    brake_confirmed = np.zeros(n, dtype=bool)
    cross_clean_confirmed = np.zeros(n, dtype=bool)
    brake_confirm_ratio = 0.7
    kd_min_separation = 2.0

    for i in range(1, n - 1):
        if brake_transition[i] and not brake_confirmed[i]:
            ref_range = float(range_[i - 1])
            ref_ok = ref_range > 0 and np.isfinite(ref_range)
            # evidencia de continuación VISIBLE en i (sin mirar adelante)
            context_ok = bool(cruce_en_zona[i]) or bool(cross_ago[i] == 0) or bool(brake_transition[i - 1])
            if ref_ok and context_ok and float(range_[i]) < brake_confirm_ratio * ref_range:
                brake_confirmed[i] = True

        if cruce_en_zona[i] and not cross_clean_confirmed[i]:
            # estado observable en i: separación suficiente y fuera de zona muerta
            kd_ok = np.isfinite(kd_dist[i]) and float(kd_dist[i]) >= kd_min_separation
            in_extreme = (k[i] <= 20.0 or k[i] >= 80.0) and (d[i] <= 20.0 or d[i] >= 80.0)
            if kd_ok and in_extreme:
                cross_clean_confirmed[i] = True

    out = pd.DataFrame({
        "time": df["time"],
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "body": body,
        "body_ratio": body_ratio,
        "range": range_,
        "range_pct": range_pct,
        "atr": atr,
        "body_n": body_n,
        "rvol": rvol,
        "trend": trend,
        "brake_mask": brake_mask,
        "brake_transition": brake_transition,
        "brake_confirmed": brake_confirmed,
        "impulse_net": impulse_net,
        "k": k,
        "d": d,
        "kd_dist": kd_dist,
        "cross_ago": cross_ago,
        "cruce_en_zona": cruce_en_zona,
        "cross_clean_confirmed": cross_clean_confirmed,
        "hammer_15m": hammer,
        "hammer_inv_15m": inv_hammer,
        "brake_ratio": brake_ratio,
        "htf_bias": htf_bias,
        "idx": np.arange(n),
        "split": split_mask,
    })
    return out
