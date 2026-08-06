"""Ejecuta EXP-003: freno en zona POI + martillo M15 desde datos crudos M15 multi-par."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.compute_features import build_feature_frame, load_m15

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
REPORT_DIR = Path("src/strategy_lab/results/exp_003")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]


def main() -> None:
    all_events = []
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        
        brake_transition = feats["brake_transition"].values
        cruce_en_zona = feats["cruce_en_zona"].values
        hammer = feats["hammer_15m"].values
        
        mask = brake_transition & cruce_en_zona & hammer
        indices = np.where(mask)[0]
        
        pair_events = []
        for idx in indices:
            if idx + 1 >= len(feats):
                continue
            
            hammer_window = feats.loc[idx:idx + 3, "hammer_15m"]
            hammer_in_window = bool(hammer_window.any())
            if not hammer_in_window:
                continue
            
            entry_row = feats.iloc[idx + 1]
            outcome_window = feats.iloc[idx + 2 : idx + 8]
            if len(outcome_window) == 0:
                continue
            
            direction = 1 if feats.iloc[idx]["impulse_net"] < 0 else -1
            if direction == 1:
                win = 1 if entry_row["close"] < feats.iloc[idx + 2]["close"] else 0
            else:
                win = 1 if entry_row["close"] > feats.iloc[idx + 2]["close"] else 0
            
            pair_events.append({
                "asset": pair,
                "timestamp": entry_row["time"],
                "win": win,
                "profit": 1.0 if win else -1.0,
                "expected_value": 1.0 if win else -1.0,
                "timeframe": "M15",
                "brake_idx": int(feats.iloc[idx]["idx"]),
                "cross_separation": np.nan,
                "minutes_brake_to_cross": np.nan,
                "body_n_brake": np.nan,
            })
        
        events_df = pd.DataFrame(pair_events)
        print(f"{pair}: {len(events_df)} events")
        all_events.append(events_df)
    
    events = pd.concat(all_events, ignore_index=True)
    if len(events) < 20:
        print(f"[warn] Too few events for strong conclusions: {len(events)}; continuing.")
    
    events["split"] = ["train"] * (len(events) // 2) + ["test"] * (len(events) - len(events) // 2)
    print(f"\nTotal eventos: {len(events)}")
    
    baseline_comparison = {
        "baseline_id": "BASELINE-EDIFICIO",
        "baseline_version": "1.0",
        "deltas": {
            "win_rate": round(float(events["win"].mean()) - 0.371, 4),
            "expected_value": round(float(events["expected_value"].sum()), 4),
        },
    }
    
    baseline = Baseline(
        id="BASELINE-EDIFICIO",
        version="1.0",
        created_at="2026-08-04T00:00:00Z",
        author="hermes",
        description="Baseline edificio eventos reales",
        metrics={"win_rate": 0.371, "expected_value": 0.0},
        dataset_checksum="edificio-events-946",
    )
    baseline_manager = BaselineManager()
    baseline_manager.register(baseline)
    registry = ExperimentRegistry(baseline_manager=baseline_manager)

    artifacts = run_experiment(
        experiment_id="EXP-003",
        events=events,
        hypothesis="H1-brake-en-zona-POI-con-hammer-M15",
        tribunal_version="1.0",
        baseline_id="BASELINE-EDIFICIO",
        baseline_version="1.0",
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=REPORT_DIR,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError("EXP-003 did not produce a gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report

    print("\nExperimento: EXP-003")
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
