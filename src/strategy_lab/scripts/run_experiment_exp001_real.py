"""Ejecuta EXP-001 con el dataset real del Laboratorio."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry

REAL_DATA_PATH = Path("src/strategy_lab/results/edificio_events.csv")
REPORT_DIR = Path("src/strategy_lab/results/exp_001")


def load_events() -> pd.DataFrame:
    events = pd.read_csv(REAL_DATA_PATH)
    rename_map = {}
    if "win" in events.columns and "profit" not in events.columns:
        events["profit"] = events["win"].map({1: 1.0, 0: -1.0})
    if "direction" in events.columns and "expected_value" not in events.columns:
        events["expected_value"] = events["direction"].map({"BUY": 1.0, "SELL": -1.0})
    if "brake_time" in events.columns and "timestamp" not in events.columns:
        events["timestamp"] = pd.to_datetime(events["brake_time"])
    if "timeframe" not in events.columns:
        events["timeframe"] = "M15"
    if "asset" not in events.columns:
        events["asset"] = "UNKNOWN"
    required = {"split", "profit", "expected_value", "timeframe", "timestamp", "asset"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"Event dataset missing columns: {missing}")
    return events


def main() -> None:
    events = load_events()
    if events.empty:
        raise RuntimeError("Event dataset is empty")

    win_mean = float(events["win"].mean())
    ev_mean = float(events["expected_value"].mean())
    baseline_comparison = {
        "baseline_id": "BASELINE-EDIFICIO",
        "baseline_version": "1.0",
        "deltas": {
            "win_rate": round(win_mean - 0.371, 4),
            "expected_value": round(ev_mean, 4),
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
        experiment_id="EXP-001-REAL",
        events=events,
        hypothesis="H1-EDIFICIO-REAL",
        tribunal_version="1.0",
        baseline_id="BASELINE-EDIFICIO",
        baseline_version="1.0",
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=REPORT_DIR,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError("EXP-001-REAL did not produce a gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report

    print("Experimento: EXP-001-REAL")
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
    print(f"Detalles robustez: {robustness.results}")
    if artifacts.report_path:
        print(f"Informe: {artifacts.report_path}")


if __name__ == "__main__":
    main()
