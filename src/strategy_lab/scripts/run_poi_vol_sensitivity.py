"""Sensor de sensibilidad volumétrica en el eje Y + aprendizaje incremental del POI.

Eje Y como sensor de porcentaje de volumen: para cada nivel de precio,
se mide el "volumen de choque" = porcentaje del volumen total acumulado
en ese nivel cuando el precio lo toca. Luego, un clasificador incremental
aprende, vela por vela, si el POI producirá rebote o break.

Uso: solo lectura sobre parquet de SMC-SYSTEMS. No toca el edificio.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

from strategy_lab.poi_behavior import analyze_levels, swing_levels_causal, DEFAULT_CFG
from strategy_lab.brake_eval import compute_brake_and_rebote

SMC_ROOT = Path(r"C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw")
PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIP = {p: (0.01 if p.endswith("JPY") else 1e-4) for p in PAIRS}

R = 5  # ventana de desenlace


class VolumetricYSensor:
    """Mapa de sensibilidad volumétrica en el eje Y (precio).

    Crea bins de precio y acumula ticks/volumen por bin. Devuelve
    un perfil normalizado (porcentaje del volumen total) para cada
    nivel de precio.
    """

    def __init__(self, n_bins: int = 200):
        self.n_bins = int(n_bins)
        self.edges: np.ndarray | None = None
        self.profile: np.ndarray | None = None
        self.total_ticks: float = 0.0

    def fit(self, lows: np.ndarray, highs: np.ndarray, ticks: np.ndarray):
        l = np.asarray(lows, float)
        h = np.asarray(highs, float)
        t = np.asarray(ticks, float)
        if l.size == 0:
            return self
        pmin = float(l.min())
        pmax = float(h.max())
        if pmax <= pmin:
            return self
        edges = np.linspace(pmin, pmax, self.n_bins + 1)
        profile = np.zeros(self.n_bins, dtype=float)
        for i in range(len(l)):
            lo = int(np.searchsorted(edges, l[i], side="right") - 1)
            hi = int(np.searchsorted(edges, h[i], side="left"))
            lo = max(lo, 0)
            hi = min(hi, self.n_bins - 1)
            if hi < lo:
                continue
            w = t[i] / max(hi - lo + 1, 1)
            profile[lo:hi + 1] += w
        total = float(profile.sum())
        if total > 0:
            profile = profile / total
        self.edges = edges
        self.profile = profile
        self.total_ticks = float(t.sum())
        return self

    def sensitivity_at(self, price: float) -> float:
        if self.edges is None or self.profile is None:
            return 0.0
        price = float(price)
        if price <= self.edges[0] or price >= self.edges[-1]:
            return 0.0
        idx = int(np.searchsorted(self.edges, price, side="right") - 1)
        idx = max(0, min(idx, self.n_bins - 1))
        return float(self.profile[idx])

    def pct_range(self, low: float, high: float) -> float:
        if self.edges is None or self.profile is None:
            return 0.0
        lo = max(float(low), float(self.edges[0]))
        hi = min(float(high), float(self.edges[-1]))
        if hi <= lo:
            return 0.0
        mask = (self.edges[:-1] >= lo) & (self.edges[1:] <= hi)
        return float(self.profile[mask].sum()) if mask.any() else 0.0


def _make_features(close_i: float, dist_norm: float, sens: float,
                   vol_i: float, ret_i: float, vol_range: float) -> np.ndarray:
    return np.array([[close_i, dist_norm, sens, vol_i, ret_i, vol_range]], dtype=float)


def run_pair(asset: str, train_frac: float = 0.6):
    df = pd.read_parquet(SMC_ROOT / f"{asset}_M15.parquet")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    o = df["open"].values.astype(float)
    h = df["high"].values.astype(float)
    l = df["low"].values.astype(float)
    c = df["close"].values.astype(float)
    ticks = pd.to_numeric(df["tick_volume"], errors="coerce").fillna(0).values.astype(float)
    n = len(c)
    if n < 200:
        return {"asset": asset, "error": "short"}

    # sensor Y: perfil de volumen por precio en toda la serie
    sensor = VolumetricYSensor(n_bins=200).fit(l, h, ticks)

    # POI swing causal
    fl, ce, af, at = swing_levels_causal(h, l, min_touches=2, tol_pips=5.0,
                                          lookback=100, pip_size=PIP[asset])

    # Frenos estrictos para target
    strict_cfg = {
        "impulse": {"window": 15, "min_pips": 5.0},
        "brake": {"fwd": 3, "max_advance_frac": 0.5, "require_alternation": False},
        "rebote": {"fwd": 2, "min_pips": 0.5},
    }
    feat_strict = compute_brake_and_rebote(o, h, l, c, strict_cfg)
    brake_strict = feat_strict["brake_mask"].astype(bool)

    # Generar secuencia de entrenamiento: una fila por toque direccional
    X_list: list[np.ndarray] = []
    y_list: list[int] = []
    centers = 0.5 * (fl + ce)
    active = np.column_stack([af, at])
    prev_c = np.concatenate([[c[0]], c[:-1]])

    for i in range(n):
        # toque a alguna banda activa
        mask_active = (active[:, 0] <= i) & (i < active[:, 1])
        if not mask_active.any():
            continue
        in_band = (l[i] <= ce[mask_active]) & (h[i] >= fl[mask_active])
        if not in_band.any():
            continue
        k = np.flatnonzero(in_band)[0]
        fl_i = float(fl[mask_active][k])
        ce_i = float(ce[mask_active][k])
        center_i = float(centers[mask_active][k])
        ab = bool(prev_c[i] > ce[mask_active][k])

        # target: rebote (1) o break (0) en próximas R velas
        seg = slice(i + 1, min(i + R, n - 1) + 1)
        if seg.start >= n:
            continue
        sub_c = c[seg]
        if ab:
            reb = np.flatnonzero(sub_c >= c[i] + DEFAULT_CFG["reb_pips"] * PIP[asset])
            brk = np.flatnonzero(sub_c <= fl_i - DEFAULT_CFG["break_tol"] * PIP[asset])
        else:
            reb = np.flatnonzero(sub_c <= c[i] - DEFAULT_CFG["reb_pips"] * PIP[asset])
            brk = np.flatnonzero(sub_c >= ce_i + DEFAULT_CFG["break_tol"] * PIP[asset])
        if reb.size and (not brk.size or int(reb[0]) <= int(brk[0])):
            y = 1
        elif brk.size:
            y = 0
        else:
            continue

        dist_norm = abs(c[i] - center_i) / max(abs(center_i), 1e-9)
        sens = sensor.sensitivity_at(c[i])
        vol_i = float(ticks[i])
        ret_i = float(c[i] - c[i - 1]) if i > 0 else 0.0
        vol_range = float(ticks[max(0, i - 15):i + 1].sum())
        X_list.append(np.array([c[i], dist_norm, sens, vol_i, ret_i, vol_range], dtype=float))
        y_list.append(y)

    if len(X_list) < 20:
        return {"asset": asset, "error": "too_few_samples", "n_samples": len(X_list)}
    X = np.vstack(X_list)
    y = np.array(y_list, dtype=int)

    # Split train/test
    split = int(len(X) * train_frac)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = SGDClassifier(loss="log_loss", penalty="l2", alpha=1e-4, max_iter=1, warm_start=True, random_state=42)
    classes = np.array([0, 1])
    for _ in range(10):
        clf.partial_fit(X_train_s, y_train, classes=classes)

    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)

    # Baseline: clase mayoritaria
    maj = int(np.bincount(y_train).argmax())
    baseline = float(np.mean(y_test == maj))

    return {
        "asset": asset,
        "n_samples": int(len(X)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "baseline": round(baseline, 3),
        "accuracy": round(float(acc), 3),
        "delta_vs_baseline": round(float(acc - baseline), 3),
        "rebound_rate_train": round(float(np.mean(y_train)), 3),
        "rebound_rate_test": round(float(np.mean(y_test)), 3),
    }


def main():
    rows = []
    for asset in PAIRS:
        try:
            r = run_pair(asset)
            rows.append(r)
        except Exception as e:
            rows.append({"asset": asset, "error": str(e)})

    cols = ["asset", "n_samples", "n_train", "n_test", "baseline", "accuracy", "delta_vs_baseline",
            "rebound_rate_train", "rebound_rate_test"]
    print(",".join(cols))
    for r in rows:
        if "error" in r:
            print(f"{r['asset']},,,,,,,,,ERROR={r['error']}")
            continue
        print(",".join(str(r.get(k, "")) for k in cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
