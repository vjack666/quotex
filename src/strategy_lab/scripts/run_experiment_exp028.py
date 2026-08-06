"""Ejecuta EXP-028: consistencia relajada 2/5."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.compute_features import build_feature_frame, load_m15

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
REPORT_DIR = Path("src/strategy_lab/results/exp_028")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371
HORIZONS = [1, 2, 3, 4, 5]
MIN_CONSISTENT_WINS = 2
OUTCOME_HORIZON = 2


def evaluate(feats: pd.DataFrame, pair: str) -> pd.DataFrame:
    mask = feats["brake_transition"].values
    n = len(feats)
    valid = []
    for idx in np.where(mask)[0]:
        if idx + max(HORIZONS) + 1 >= n:
            continue
        wins = 0
        entry_close = feats.iloc[idx + 1]["close"]
        direction = 1 if feats.iloc[idx]["impulse_net"] < 0 else -1
        for h in HORIZONS:
            outcome = feats.iloc[idx + 1 + h]["close"]
            if direction == 1:
                wins += 1 if entry_close < outcome else 0
            else:
                wins += 1 if entry_close > outcome else 0

        if wins < MIN_CONSISTENT_WINS:
            continue

        outcome = feats.iloc[idx + 1 + OUTCOME_HORIZON]["close"]
        if direction == 1:
            win = 1 if entry_close < outcome else 0
        else:
            win = 1 if entry_close > outcome else 0

        valid.append({
            "asset": pair,
            "timestamp": feats.iloc[idx]["time"],
            "win": win,
            "profit": 1.0 if win else -1.0,
            "expected_value": 1.0 if win else -1.0,
        })
    return pd.DataFrame(valid)


def main() -> None:
    all_events = []
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        events = evaluate(feats, pair)
        if len(events) > 0:
            all_events.append(events)
        print(f"{pair}: {len(events)} events")

    events = pd.concat(all_events, ignore_index=True)
    if len(events) < 20:
        print(f"[warn] Too few events for strong conclusions: {len(events)}; continuing.")

    print(f"\nTotal eventos: {len(events)}")

    baseline_comparison = {
        "baseline_id": BASELINE_ID,
        "baseline_version": BASELINE_VERSION,
        "deltas": {
            "win_rate": round(float(events["win"].mean()) - BASELINE_WR, 4),
            "expected_value": round(float(events["expected_value"].sum()), 4),
        },
    }

    baseline = Baseline(
        id=BASELINE_ID,
        version=BASELINE_VERSION,
        created_at="2026-08-04T00:00:00Z",
        author="hermes",
        description="Baseline edificio eventos reales",
        metrics={"win_rate": BASELINE_WR, "expected_value": 0.0},
        dataset_checksum="edificio-events-946",
    )
    baseline_manager = BaselineManager()
    baseline_manager.register(baseline)
    registry = ExperimentRegistry(baseline_manager=baseline_manager)

    artifacts = run_experiment(
        experiment_id="EXP-028",
        events=events,
        hypothesis="H1-brake-transition-consistency-2-5",
        tribunal_version="1.0",
        baseline_id=BASELINE_ID,
        baseline_version=BASELINE_VERSION,
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=REPORT_DIR,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError("EXP-028 did not produce a gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report

    print("\nExperimento: EXP-028")
    print(f"Eventos: {evidence.events_total}")
    print(f"Train/test: {evidence.events_train}/{evidence.events_test}")
    print(f"Veredicto tribunal: {decision.verdict}")
    print(f"Criterios pasados: {decision.criteria_passed}")
    print(f"Criterios fallidos: {decision.criteria_failed}")
    print(f"Criterios rotos: {decision.failed_criteria}")
    print(f"Warnings: {decision.warnings}")
    print(f"Win rate: {evidence.win_rate:.4f}")
    print(f"EV: {evidence.expected_value:.4f}")
    print(f"Profit factor: {evidence.profit_factor}")
    print(f"p-value: {evidence.p_value_win_rate:.4f}")
    print(f"Power: {evidence.details.get('power')}")
    print(f"Robustez: {robustness.passed_count}/{robustness.total_tests}")
    if artifacts.report_path:
        print(f"Informe: {artifacts.report_path}")


if __name__ == "__main__":
    main()
