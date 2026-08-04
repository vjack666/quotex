"""Ejecuta EXP-034B: pipeline secuencial brake_confirmed -> cross_clean_confirmed."""
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
REPORT_DIR = Path("src/strategy_lab/results/exp_034b")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371
OUTCOME_HORIZON = 2
WINDOW = 12


def evaluate_sequence(feats: pd.DataFrame, pair: str) -> pd.DataFrame:
    df = feats.copy()
    df = df.dropna(subset=["brake_confirmed", "cross_clean_confirmed", "impulse_net", "close", "time"]).reset_index(drop=True)
    n = len(df)
    events = []
    brake_indices = np.where(np.asarray(df["brake_confirmed"].values, dtype=bool))[0].tolist()

    for idx in brake_indices:
        cross_idx = None
        for j in range(idx + 1, min(idx + WINDOW + 1, n)):
            if bool(df.iat[j, df.columns.get_loc("cross_clean_confirmed")]):
                cross_idx = j
                break
        if cross_idx is None:
            continue
        entry_idx = cross_idx + 1
        if entry_idx >= n:
            continue
        outcome_idx = min(cross_idx + OUTCOME_HORIZON + 1, n - 1)
        entry_close = float(df.iat[entry_idx, df.columns.get_loc("close")])
        outcome_close = float(df.iat[outcome_idx, df.columns.get_loc("close")])
        direction = 1 if float(df.iat[idx, df.columns.get_loc("impulse_net")]) < 0 else -1
        win = 1 if (direction == 1 and entry_close < outcome_close) or (direction == -1 and entry_close > outcome_close) else 0
        events.append({
            "asset": pair,
            "timestamp": df.iat[cross_idx, df.columns.get_loc("time")],
            "brake_idx": int(idx),
            "cross_idx": int(cross_idx),
            "win": win,
            "profit": 1.0 if win else -1.0,
            "expected_value": 1.0 if win else -1.0,
        })
    return pd.DataFrame(events)


def compute_metrics(events: pd.DataFrame) -> Dict[str, float]:
    if len(events) == 0:
        return {"win_rate": float("nan"), "expected_value": float("nan"), "profit_factor": float("nan"), "events": 0}
    wr = float(events["win"].mean())
    ev = float(events["expected_value"].sum())
    pf = float(events.loc[events["profit"] > 0, "profit"].sum() / abs(events.loc[events["profit"] < 0, "profit"].sum())) if (events["profit"] < 0).any() else float("inf")
    return {"win_rate": wr, "expected_value": ev, "profit_factor": pf, "events": len(events)}


def main() -> None:
    all_events = []
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        events = evaluate_sequence(feats, pair)
        all_events.append(events)
        print(f"{pair}: {len(events)} events")

    df_all = pd.concat(all_events, ignore_index=True)
    metrics = compute_metrics(df_all)
    print(f"pipeline secuencial confirmado: WR={metrics['win_rate']:.4f}, EV={metrics['expected_value']:.4f}, PF={metrics['profit_factor']:.4f}, n={metrics['events']}")


if __name__ == "__main__":
    main()
