"""Ejecuta EXP-013: brake_transition + kd_dist mínimo."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry
from strategy_lab.compute_features import build_feature_frame, load_m15

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
REPORT_DIR = Path("src/strategy_lab/results/exp_013")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

BASELINE_ID = "BASELINE-EDIFICIO"
BASELINE_VERSION = "1.0"
BASELINE_WR = 0.371

KD_THRESHOLDS = [0.01, 0.02, 0.05, 0.1]


def evaluate_variant(feats: pd.DataFrame, kd_th: float) -> pd.DataFrame:
    mask = feats["brake_transition"].values
    kd_dist = np.abs(feats["k"].values - feats["d"].values)
    indices = np.where((mask) & (kd_dist >= kd_th))[0]
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


def run_single(kd_th: float) -> dict:
    all_events = []
    for pair in PAIRS:
        df = load_m15(pair, DATA_DIR)
        feats = build_feature_frame(df)
        events = evaluate_variant(feats, kd_th)
        if len(events) > 0:
            events["asset"] = pair
            all_events.append(events)
        print(f"kd_th={kd_th}: {pair} -> {len(events)} events")

    events_df = pd.concat(all_events, ignore_index=True)
    events_df["split"] = ["train"] * (len(events_df) // 2) + ["test"] * (len(events_df) - len(events_df) // 2)

    baseline_comparison = {
        "baseline_id": BASELINE_ID,
        "baseline_version": BASELINE_VERSION,
        "deltas": {
            "win_rate": round(float(events_df["win"].mean()) - BASELINE_WR, 4),
            "expected_value": round(float(events_df["expected_value"].sum()), 4),
        },
    }

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
    registry = ExperimentRegistry(baseline_manager=baseline_manager)

    report_dir = REPORT_DIR / f"kd_{kd_th}"
    report_dir.mkdir(parents=True, exist_ok=True)

    artifacts = run_experiment(
        experiment_id=f"EXP-013-KD-{kd_th}",
        events=events_df,
        hypothesis=f"H1-brake-kd-{kd_th}",
        tribunal_version="1.0",
        baseline_id=BASELINE_ID,
        baseline_version=BASELINE_VERSION,
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=report_dir,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError(f"kd_th={kd_th} missing gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report
    return {
        "kd_threshold": kd_th,
        "events_total": evidence.events_total,
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


def main() -> None:
    summaries = []
    for kd_th in KD_THRESHOLDS:
        summary = run_single(kd_th)
        summaries.append(summary)
        print(
            f"kd={kd_th}: verdict={summary['verdict']}, WR={summary['win_rate']:.4f}, "
            f"EV={summary['ev']:.4f}, PF={summary['pf']:.4f}, events={summary['events_total']}"
        )

    summary_df = pd.DataFrame(summaries)
    summary_path = REPORT_DIR / "EXP-013_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\nResumen guardado en: {summary_path}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
