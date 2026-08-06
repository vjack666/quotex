"""Backtest vela-por-vela del Edificio (P1 brake -> P2 confirm -> P3 cruce no-sticky -> martillo -> entrada -> WIN/LOSS).

Genera dataset features+label, reporte winrate baseline y CSV/Parquet.
Sin look-ahead. No toca bot en vivo. No entrena modelo.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from strategy_lab.brake_eval import compute_brake_and_rebote
from strategy_lab.compute_features import (
    PIP_FACTOR,
    SMC_ROOT,
    build_feature_frame,
    detect_hammer,
    load_htf,
    load_m15,
)

# Config por defecto
DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
R = 5
MAX_LOOKAHEAD = 40
MIN_CROSS_SEPARATION = 2.0
MAINTAIN_WINDOW = 5
BODY_N_MAX = 0.60
BRAKE_RATIO_MAX = 1.0
TRAIN_RATIO = 0.70


def run_backtest(
    pairs: List[str] = DEFAULT_PAIRS,
    r: int = R,
    max_lookahead: int = MAX_LOOKAHEAD,
    min_separation: float = MIN_CROSS_SEPARATION,
    maintain_window: int = MAINTAIN_WINDOW,
    body_n_max: float = BODY_N_MAX,
    brake_ratio_max: float = BRAKE_RATIO_MAX,
    train_ratio: float = TRAIN_RATIO,
    root: Path = SMC_ROOT,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for asset in pairs:
        df = build_feature_frame(load_m15(asset, root), load_htf(asset, root))
        if df.empty:
            continue
        o = df["open"].values
        h = df["high"].values
        l = df["low"].values
        c = df["close"].values

        k = df["k"].values
        d = df["d"].values
        kd_dist = df["kd_dist"].values
        hammer = df["hammer_15m"].values
        inv_hammer = df["hammer_inv_15m"].values
        brake_mask = df["brake_mask"].values.astype(bool)
        brake_transition = df["brake_transition"].values.astype(bool)
        impulse_net = df["impulse_net"].values
        body_n = df["body_n"].values
        brake_ratio = df["brake_ratio"].values
        cross_ago = df["cross_ago"].values
        cruce_en_zona = df["cruce_en_zona"].values
        htf_bias = df["htf_bias"].values
        trend = df["trend"].values
        rvol = df["rvol"].values

        pip = PIP_FACTOR.get(asset, 1e-4)
        n = len(c)

        candidates = np.flatnonzero(brake_transition).tolist()

        for i in candidates:
            if i < 20:
                continue
            if not np.isfinite(k[i]) or not np.isfinite(d[i]):
                continue
            if body_n[i] > body_n_max:
                continue
            if brake_ratio[i] > brake_ratio_max:
                continue

            direction = "CALL" if impulse_net[i] < 0 else "PUT"
            extreme_k = 20.0 if direction == "CALL" else 80.0

            found_cross = False
            cross_idx = None
            for j in range(i + 1, min(i + max_lookahead + 1, n - 1)):
                if not (np.isfinite(k[j]) and np.isfinite(d[j]) and np.isfinite(k[j - 1]) and np.isfinite(d[j - 1])):
                    continue
                sep = float(kd_dist[j])
                if sep < min_separation:
                    continue
                if direction == "CALL" and k[j] <= extreme_k and k[j - 1] <= d[j - 1] and k[j] > d[j]:
                    found_cross = True
                    cross_idx = j
                    break
                if direction == "PUT" and k[j] >= extreme_k and k[j - 1] >= d[j - 1] and k[j] < d[j]:
                    found_cross = True
                    cross_idx = j
                    break

            if not found_cross or cross_idx is None:
                continue

            # sticky check + hammer confirmation window
            sticky = False
            confirm_idx = None
            for jj in range(cross_idx + 1, min(cross_idx + 1 + maintain_window, n - 1)):
                if not (np.isfinite(k[jj]) and np.isfinite(d[jj]) and np.isfinite(k[jj - 1]) and np.isfinite(d[jj - 1])):
                    continue
                if float(kd_dist[jj]) < min_separation:
                    sticky = True
                    break
                valid = inv_hammer[jj] if direction == "CALL" else hammer[jj]
                if bool(valid):
                    confirm_idx = jj
                    break

            if sticky or confirm_idx is None:
                continue

            entry_idx = confirm_idx + 1
            if entry_idx + r >= n:
                continue

            seg = slice(entry_idx, entry_idx + r)
            sub_c = c[seg]
            win = False
            if direction == "CALL" and np.any(sub_c >= c[confirm_idx] + 5 * pip):
                win = True
            elif direction == "PUT" and np.any(sub_c <= c[confirm_idx] - 5 * pip):
                win = True

            # features snapshot causal: usamos valores hasta brake/entry según feature.
            # HTF bias y trend en brake. Hammer flag en confirm.
            htf_bias_val = float(htf_bias[i]) if np.isfinite(htf_bias[i]) else 0.0
            htf_sign = "NEUTRO" if abs(htf_bias_val) < 1e-9 else ("ALCISTA" if htf_bias_val > 0 else "BAJISTA")

            rows.append({
                "asset": asset,
                "brake_idx": int(i),
                "cross_idx": int(cross_idx),
                "confirm_idx": int(confirm_idx),
                "brake_time": df.loc[i, "time"],
                "direction": direction,
                "win": int(win),
                "minutes_brake_to_cross": (cross_idx - i) * 15,
                "minutes_brake_to_entry": (confirm_idx - i) * 15,
                "body_n_brake": float(body_n[i]),
                "brake_ratio": float(brake_ratio[i]),
                "k_brake": float(k[i]),
                "d_brake": float(d[i]),
                "kd_dist_brake": float(kd_dist[i]),
                "extreme_flag": int((direction == "CALL" and k[i] <= 20) or (direction == "PUT" and k[i] >= 80)),
                "cruce_en_zona_brake": int(bool(cruce_en_zona[i])),
                "cross_ago_brake": float(cross_ago[i]) if np.isfinite(cross_ago[i]) else np.nan,
                "cross_separation": float(kd_dist[cross_idx]),
                "k_cross": float(k[cross_idx]),
                "d_cross": float(d[cross_idx]),
                "hammer_flag": int(bool(inv_hammer[confirm_idx] if direction == "CALL" else hammer[confirm_idx])),
                "trend_brake": float(trend[i]) if np.isfinite(trend[i]) else 0.0,
                "rvol_brake": float(rvol[i]) if np.isfinite(rvol[i]) else 1.0,
                "htf_bias_brake": float(htf_bias_val),
                "htf_sign": htf_sign,
                "split": "train" if i < int(float(n) * train_ratio) else "test",
            })

    events = pd.DataFrame(rows)
    if events.empty:
        return events
    events = events.sort_values(["asset", "brake_time"]).reset_index(drop=True)
    return events


def summarize(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        print("Sin eventos. Revisar filtros.")
        return pd.DataFrame()


def save_outputs(events: pd.DataFrame, out_dir: Path = Path("src/strategy_lab/results")) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "edificio_events.csv"
    parquet_path = out_dir / "edificio_events.parquet"
    events.to_csv(csv_path, index=False)
    try:
        events.to_parquet(parquet_path, index=False)
    except Exception as exc:
        print(f"[warn] no se pudo guardar parquet: {exc}")
        parquet_path = None
    print(f"CSV guardado en {csv_path}")
    if parquet_path:
        print(f"Parquet guardado en {parquet_path}")
    return csv_path, parquet_path


def main(pairs: Optional[List[str]] = None) -> int:
    pairs = pairs or DEFAULT_PAIRS
    events = run_backtest(pairs=pairs)
    if events.empty:
        return 1
    summarize(events)
    save_outputs(events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
