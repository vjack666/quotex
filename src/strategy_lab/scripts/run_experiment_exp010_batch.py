"""Ejecuta EXP-010 batch: 10 variantes de filtros de calidad del freno."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.compute_features import build_feature_frame, load_m15

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
BASE_REPORT_DIR = Path("src/strategy_lab/results/exp_010_batch")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

THRESHOLDS = [
    (0.5, 1.2),
    (0.8, 1.2),
    (1.0, 1.2),
    (1.2, 1.2),
    (1.5, 1.2),
    (0.8, 1.5),
    (1.0, 1.5),
    (1.2, 1.5),
    (1.5, 1.5),
    (2.0, 2.0),
]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371


def evaluate_variant(feats: pd.DataFrame, body_n_th: float, brake_ratio_th: float) -> pd.DataFrame:
    mask = feats["brake_transition"].values
    body_n = feats["body_n"].values
    brake_ratio = feats["brake_ratio"].values
    indices = np.where((mask) & (body_n >= body_n_th) & (brake_ratio >= brake_ratio_th))[0]
    pair_events = []
    for idx in indices:
        if idx + 1 >= len(feats) or idx + 2 >= len(feats):
            continue
        entry_row = feats.iloc[idx + 1]
        outcome = feats.iloc[idx + 2]
        direction = 1 if feats.iloc[idx]["impulse_net"] < 0 else -1
        if direction == 1:
            win = 1 if entry_row["close"] < outcome["close"] else 0
        else:
            win = 1 if entry_row["close"] > outcome["close"] else 0
        pair_events.append({
            "win": win,
            "profit": 1.0 if win else -1.0,
            "expected_value": 1.0 if win else -1.0,
        })
    return pd.DataFrame(pair_events)


def main() -> None:
    all_summaries = []
    baseline_manager = BaselineManager()
    baseline = Baseline(
        id=BASELINE_ID,
        version=BASELINE_VERSION,
        created_at="2026-08-04T00:00:00Z",
        author="hermes",
        description="Baseline edificio eventos reales",
        metrics={"win_rate": BASELINE_WR, "expected_value": 0.0},
        dataset_checksum="edificio-events-946",
    )
    baseline_manager.register(baseline)

    for i, (body_n_th, brake_ratio_th) in enumerate(THRESHOLDS, start=1):
        all_events = []
        for pair in PAIRS:
            df = load_m15(pair, DATA_DIR)
            feats = build_feature_frame(df)
            events = evaluate_variant(feats, body_n_th, brake_ratio_th)
            if len(events) > 0:
                events["asset"] = pair
                all_events.append(events)
            print(f"Variant {i} ({body_n_th}, {brake_ratio_th}): {pair} -> {len(events)} events")

        if not all_events:
            print(f"[warn] Variant {i} produced no events")
            continue

        events_df = pd.concat(all_events, ignore_index=True)
        if len(events_df) < 20:
            print(f"[warn] Variant {i}: too few events ({len(events_df)}); continuing.")

        events_df["split"] = ["train"] * (len(events_df) // 2) + ["test"] * (len(events_df) - len(events_df) // 2)
        report_dir = BASE_REPORT_DIR / f"variant_{i:02d}"
        report_dir.mkdir(parents=True, exist_ok=True)

        baseline_comparison = {
            "baseline_id": BASELINE_ID,
            "baseline_version": BASELINE_VERSION,
            "deltas": {
                "win_rate": round(float(events_df["win"].mean()) - BASELINE_WR, 4),
                "expected_value": round(float(events_df["expected_value"].sum()), 4),
            },
        }

        registry = ExperimentRegistry(baseline_manager=baseline_manager)

        artifacts = run_experiment(
            experiment_id=f"EXP-010-VARIANT-{i:02d}",
            events=events_df,
            hypothesis=f"H1-brake-quality-body_n_{body_n_th}-ratio_{brake_ratio_th}",
            tribunal_version="1.0",
            baseline_id=BASELINE_ID,
            baseline_version=BASELINE_VERSION,
            registry=registry,
            baseline_manager=baseline_manager,
            report_dir=report_dir,
            baseline_comparison=baseline_comparison,
        )

        if artifacts.gate_decision is None:
            raise RuntimeError(f"Variant {i} did not produce a gate decision")

        decision = artifacts.gate_decision
        evidence = artifacts.evidence_report
        robustness = artifacts.robustness_report
        summary = {
            "variant": i,
            "body_n_threshold": body_n_th,
            "brake_ratio_threshold": brake_ratio_th,
            "events_total": evidence.events_total,
            "train": evidence.events_train,
            "test": evidence.events_test,
            "verdict": decision.verdict,
            "criteria_passed": decision.criteria_passed,
            "criteria_failed": decision.criteria_failed,
            "win_rate": evidence.win_rate,
            "ev": evidence.expected_value,
            "pf": evidence.profit_factor,
            "p_value": evidence.p_value_win_rate,
            "power": evidence.details.get("power"),
            "robustness": f"{robustness.passed_count}/{robustness.total_tests}",
            "failed_criteria": "; ".join(decision.failed_criteria),
            "warnings": "; ".join(decision.warnings),
            "report": str(artifacts.report_path),
        }
        all_summaries.append(summary)
        print(
            f"Variant {i}: verdict={decision.verdict}, WR={evidence.win_rate:.4f}, "
            f"EV={evidence.expected_value:.4f}, PF={evidence.profit_factor:.4f}, events={evidence.events_total}"
        )

    summary_df = pd.DataFrame(all_summaries)
    summary_path = BASE_REPORT_DIR / "EXP-010_batch_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\nResumen guardado en: {summary_path}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
