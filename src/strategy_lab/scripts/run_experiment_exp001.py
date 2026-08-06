"""Ejecuta EXP-001 con filtro combinado cross_separation>=4.5 y minutes_brake_to_cross>=16."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry

REAL_DATA_PATH = Path("src/strategy_lab/results/edificio_events.csv")
REPORT_DIR = Path("src/strategy_lab/results/exp_001")


def main() -> None:
    events = pd.read_csv(REAL_DATA_PATH)
    events["profit"] = events["win"].map({1: 1.0, 0: -1.0})
    events["expected_value"] = events["profit"]
    events["timeframe"] = "M15"
    events["asset"] = events.get("asset", "EURUSD")
    events["timestamp"] = pd.to_datetime(events.get("brake_time", events.get("timestamp", "2026-01-01")))
    
    filtered = events[(events["cross_separation"] >= 4.5) & (events["minutes_brake_to_cross"] >= 16)].copy()
    print(f"Eventos filtrados: {len(filtered)}")
    
    baseline_comparison = {
        "baseline_id": "BASELINE-EDIFICIO",
        "baseline_version": "1.0",
        "deltas": {
            "win_rate": round(float(filtered["win"].mean()) - 0.371, 4),
            "expected_value": round(float(filtered["expected_value"].sum()), 4),
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
        experiment_id="EXP-001",
        events=filtered,
        hypothesis="H1-cross_separation>=4.5-and-time>=16",
        tribunal_version="1.0",
        baseline_id="BASELINE-EDIFICIO",
        baseline_version="1.0",
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=REPORT_DIR,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError("EXP-001 did not produce a gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report

    print("Experimento: EXP-001")
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
