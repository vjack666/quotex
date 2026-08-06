"""Ejecuta EXP-004: pipeline completo Edificio desde datos crudos M15 multi-par."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.compute_features import build_feature_frame, load_m15

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
REPORT_DIR = Path("src/strategy_lab/results/exp_004")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]


def main() -> None:
    all_events = []
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        
        brake_transition = feats["brake_transition"].values
        cruce_en_zona = feats["cruce_en_zona"].values
        hammer = feats["hammer_15m"].values
        cross_ago = feats["cross_ago"].values
        
        pair_events = []
        n = len(feats)
        for i in range(n):
            if not (brake_transition[i] and cruce_en_zona[i]):
                continue
            
            cross_idx = None
            for j in range(i + 1, min(i + 61, n)):
                if cruce_en_zona[j] and cross_ago[j] == 0:
                    cross_idx = j
                    break
            
            if cross_idx is None:
                continue
            
            hammer_idx = None
            for k in range(cross_idx + 1, min(cross_idx + 61, n)):
                if hammer[k]:
                    hammer_idx = k
                    break
            
            if hammer_idx is None:
                continue
            
            entry_idx = cross_idx + 1
            if entry_idx >= n:
                continue
            
            outcome_idx = entry_idx + 1
            if outcome_idx >= n:
                continue
            
            entry_row = feats.iloc[entry_idx]
            direction = 1 if feats.iloc[i]["impulse_net"] < 0 else -1
            if direction == 1:
                win = 1 if entry_row["close"] < feats.iloc[outcome_idx]["close"] else 0
            else:
                win = 1 if entry_row["close"] > feats.iloc[outcome_idx]["close"] else 0
            
            minutes_brake_to_cross = (cross_idx - i) * 15
            minutes_cross_to_hammer = (hammer_idx - cross_idx) * 15
            
            pair_events.append({
                "asset": pair,
                "timestamp": entry_row["time"],
                "win": win,
                "profit": 1.0 if win else -1.0,
                "expected_value": 1.0 if win else -1.0,
                "timeframe": "M15",
                "brake_idx": int(feats.iloc[i]["idx"]),
                "cross_idx": int(feats.iloc[cross_idx]["idx"]),
                "hammer_idx": int(feats.iloc[hammer_idx]["idx"]),
                "minutes_brake_to_cross": minutes_brake_to_cross,
                "minutes_cross_to_hammer": minutes_cross_to_hammer,
                "cross_separation": np.nan,
                "body_n_brake": np.nan,
            })
        
        print(f"{pair}: {len(pair_events)} events")
        all_events.append(pd.DataFrame(pair_events))
    
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
        experiment_id="EXP-004",
        events=events,
        hypothesis="H1-pipeline-completo-edificio",
        tribunal_version="1.0",
        baseline_id="BASELINE-EDIFICIO",
        baseline_version="1.0",
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=REPORT_DIR,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError("EXP-004 did not produce a gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report

    print("\nExperimento: EXP-004")
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
