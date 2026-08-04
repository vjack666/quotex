"""Ejecuta EXP-032: edge de brake_confirmed aislado."""
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
REPORT_DIR = Path("src/strategy_lab/results/exp_032")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371
OUTCOME_HORIZON = 2


def evaluate_variant(feats: pd.DataFrame, pair: str, confirmed_col: str) -> pd.DataFrame:
    df = feats.copy()
    df = df.dropna(subset=[confirmed_col, "impulse_net", "close", "time"]).reset_index(drop=True)
    n = len(df)
    events = []
    for idx in range(n):
        if not bool(df.iat[idx, df.columns.get_loc(confirmed_col)]):
            continue
        if idx + OUTCOME_HORIZON + 1 >= n:
            continue
        entry_close = float(df.iat[idx + 1, df.columns.get_loc("close")])
        outcome_idx = min(idx + OUTCOME_HORIZON + 1, n - 1)
        outcome_close = float(df.iat[outcome_idx, df.columns.get_loc("close")])
        direction = 1 if float(df.iat[idx, df.columns.get_loc("impulse_net")]) < 0 else -1
        win = 1 if (direction == 1 and entry_close < outcome_close) or (direction == -1 and entry_close > outcome_close) else 0
        events.append({
            "asset": pair,
            "timestamp": df.iloc[idx]["time"],
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
        events = evaluate_variant(feats, pair, "brake_confirmed")
        all_events.append(events)
        print(f"{pair}: {len(events)} events")

    df_all = pd.concat(all_events, ignore_index=True)
    metrics = compute_metrics(df_all)
    print(f"brake_confirmed: WR={metrics['win_rate']:.4f}, EV={metrics['expected_value']:.4f}, PF={metrics['profit_factor']:.4f}, n={metrics['events']}")


if __name__ == "__main__":
    main()
