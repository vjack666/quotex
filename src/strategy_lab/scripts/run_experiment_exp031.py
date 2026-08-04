"""Ejecuta EXP-031: clasificación de secuencias por variante desde brake_transition."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.compute_features import build_feature_frame, load_m15

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
REPORT_DIR = Path("src/strategy_lab/results/exp_031")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371
STOCH_EXTREME_LOW = 20
STOCH_EXTREME_HIGH = 80
MAX_WINDOW = 12
KD_MIN_SEPARATION = 2.0
OUTCOME_HORIZON = 2


def classify_sequence(feats: pd.DataFrame, start_idx: int) -> str | None:
    df = feats.copy()
    n = len(df)
    saw_extremo = False
    saw_cross = False
    saw_separation = False
    saw_hammer = False
    max_check = min(start_idx + MAX_WINDOW, n - 3)

    for i in range(start_idx + 1, max_check + 1):
        k = df.iloc[i]["k"]
        d = df.iloc[i]["d"]
        kd_dist = df.iloc[i]["kd_dist"]
        hammer = bool(df.iloc[i]["hammer_15m"])
        cross_ago = df.iloc[i]["cross_ago"]

        if not saw_extremo and (k <= STOCH_EXTREME_LOW or k >= STOCH_EXTREME_HIGH):
            saw_extremo = True
        if not saw_cross and cross_ago == 0:
            saw_cross = True
        if saw_cross and not saw_separation and kd_dist >= KD_MIN_SEPARATION:
            saw_separation = True
        if hammer:
            saw_hammer = True

        if saw_cross and saw_separation:
            break

    if saw_cross and saw_separation and saw_hammer:
        return "completa_con_martillo"
    if saw_cross and saw_separation and not saw_hammer:
        return "completa_sin_martillo"
    if saw_cross and not saw_separation:
        return "freno_cruce_sin_separacion"
    if saw_extremo and not saw_cross:
        return "freno_extremo_sin_cruce"
    if not saw_extremo:
        return "freno_sin_extremo"
    return None


def evaluate_variants(feats: pd.DataFrame, pair: str) -> Dict[str, pd.DataFrame]:
    df = feats.copy()
    df = df.dropna(subset=["brake_transition", "cross_ago", "k", "d", "kd_dist", "hammer_15m", "close", "impulse_net", "time"])
    n = len(df)
    events: Dict[str, List[Dict[str, float]]] = {}

    brake_indices = np.asarray(df["brake_transition"].values, dtype=bool)
    brake_indices = np.where(brake_indices)[0].tolist()
    for idx in brake_indices:
        if idx + MAX_WINDOW + 1 >= n:
            continue
        variant = classify_sequence(df, idx)
        if variant is None:
            continue

        entry_idx = idx + 1
        outcome_idx = min(idx + OUTCOME_HORIZON + 1, n - 1)
        if entry_idx >= n or outcome_idx >= n:
            continue

        entry_close = df.iloc[entry_idx]["close"]
        outcome_close = df.iloc[outcome_idx]["close"]
        direction = 1 if df.iloc[idx]["impulse_net"] < 0 else -1
        if direction == 1:
            win = 1 if entry_close < outcome_close else 0
        else:
            win = 1 if entry_close > outcome_close else 0

        events.setdefault(variant, []).append({
            "asset": pair,
            "timestamp": df.iloc[idx]["time"],
            "win": win,
            "profit": 1.0 if win else -1.0,
            "expected_value": 1.0 if win else -1.0,
        })

    return {k: pd.DataFrame(v) for k, v in events.items()}


def compute_metrics(events: pd.DataFrame) -> Dict[str, float]:
    if len(events) == 0:
        return {"win_rate": float("nan"), "expected_value": float("nan"), "profit_factor": float("nan"), "events": 0}
    wr = float(events["win"].mean())
    ev = float(events["expected_value"].sum())
    pf = float(events.loc[events["profit"] > 0, "profit"].sum() / abs(events.loc[events["profit"] < 0, "profit"].sum())) if (events["profit"] < 0).any() else float("inf")
    return {"win_rate": wr, "expected_value": ev, "profit_factor": pf, "events": len(events)}


def main() -> None:
    all_variants: Dict[str, List[pd.DataFrame]] = {}
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        variants = evaluate_variants(feats, pair)
        for name, events in variants.items():
            all_variants.setdefault(name, []).append(events)
        print(f"{pair}: {sum(len(v) for v in variants.values())} events -> {list(variants.keys())}")

    ranking = []
    for name, dfs in all_variants.items():
        events = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        metrics = compute_metrics(events)
        ranking.append((name, metrics))
        print(f"{name}: WR={metrics['win_rate']:.4f}, EV={metrics['expected_value']:.4f}, PF={metrics['profit_factor']:.4f}, n={metrics['events']}")

    ranking_sorted = sorted(ranking, key=lambda x: (x[1]["win_rate"], x[1]["profit_factor"]), reverse=True)

    print("\nRanking de variantes:")
    for name, metrics in ranking_sorted:
        print(f"{name}: WR={metrics['win_rate']:.4f}, EV={metrics['expected_value']:.4f}, PF={metrics['profit_factor']:.4f}, n={metrics['events']}")


if __name__ == "__main__":
    main()
