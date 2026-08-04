"""Ejecuta EXP-035: diagnóstico de cuello de botella entre brake_confirmed y cross_clean_confirmed."""
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
REPORT_DIR = Path("src/strategy_lab/results/exp_035")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371
WINDOW = 12


def diagnose(feats: pd.DataFrame, pair: str) -> Dict[str, int]:
    df = feats.copy()
    df = df.dropna(subset=["brake_confirmed", "cross_clean_confirmed"]).reset_index(drop=True)
    n = len(df)
    brake_count = int(df["brake_confirmed"].sum())
    cross_count = int(df["cross_clean_confirmed"].sum())
    both_same_idx = int((df["brake_confirmed"] & df["cross_clean_confirmed"]).sum())
    sequential = 0
    brake_indices = np.where(df["brake_confirmed"].values)[0].tolist()
    for idx in brake_indices:
        for j in range(idx + 1, min(idx + WINDOW + 1, n)):
            if bool(df.iat[j, df.columns.get_loc("cross_clean_confirmed")]):
                sequential += 1
                break
    return {
        "pair": pair,
        "brake_confirmed": brake_count,
        "cross_clean_confirmed": cross_count,
        "both_same_idx": both_same_idx,
        "sequential_within_window": sequential,
    }


def main() -> None:
    results = []
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        diag = diagnose(feats, pair)
        results.append(diag)
        print(f"{pair}: brake={diag['brake_confirmed']}, cross={diag['cross_clean_confirmed']}, same_idx={diag['both_same_idx']}, seq={diag['sequential_within_window']}")

    totals = {
        "brake_confirmed": sum(r["brake_confirmed"] for r in results),
        "cross_clean_confirmed": sum(r["cross_clean_confirmed"] for r in results),
        "both_same_idx": sum(r["both_same_idx"] for r in results),
        "sequential_within_window": sum(r["sequential_within_window"] for r in results),
    }
    print(f"\nTotal: brake={totals['brake_confirmed']}, cross={totals['cross_clean_confirmed']}, same_idx={totals['both_same_idx']}, seq={totals['sequential_within_window']}")


if __name__ == "__main__":
    main()
