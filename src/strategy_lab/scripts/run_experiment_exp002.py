"""Ejecuta EXP-002 con features derivadas de datos crudos M15 multi-par."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_lab.baseline_manager import Baseline, BaselineManager
from strategy_lab.experiment_runner import run_experiment
from strategy_lab.registry import ExperimentRegistry

DATA_DIR = Path("C:/Users/v_jac/Desktop/SMC-SYSTEMS/data/raw")
REPORT_DIR = Path("src/strategy_lab/results/exp_002")
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]


def load_pair_data(pair: str) -> pd.DataFrame:
    path = DATA_DIR / f"{pair}_M15.parquet"
    df = pd.read_parquet(path)
    df = df.rename(columns={"time": "timestamp", "tick_volume": "volume"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["asset"] = pair
    df["timeframe"] = "M15"
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = df["high"] - df["low"]
    df["body_ratio"] = np.where(df["range"] > 0, df["body"] / df["range"], 0.0)
    df["returns"] = df["close"].pct_change()
    df["volatility"] = df["returns"].rolling(20).std()
    df["ema_fast"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=50, adjust=False).mean()
    vol_threshold = df["volatility"].quantile(0.75)
    df["structural_signal"] = (
        (df["ema_fast"] > df["ema_slow"]) &
        (df["body_ratio"] > 0.5) &
        (df["volatility"] > vol_threshold)
    )
    return df


def generate_events(df: pd.DataFrame, pair: str) -> pd.DataFrame:
    signal_indices = df.index[df["structural_signal"]].tolist()
    events = []
    for idx in signal_indices:
        if idx + 1 >= len(df):
            continue
        entry = df.iloc[idx + 1]
        future = df.iloc[idx + 2 : idx + 8]
        if len(future) == 0:
            continue
        win = 1 if entry["close"] < future["close"].iloc[-1] else 0
        events.append({
            "asset": pair,
            "timestamp": entry["timestamp"],
            "win": win,
            "profit": 1.0 if win else -1.0,
            "expected_value": 1.0 if win else -1.0,
            "timeframe": "M15",
            "ema_fast": df.iloc[idx]["ema_fast"],
            "ema_slow": df.iloc[idx]["ema_slow"],
            "body_ratio": df.iloc[idx]["body_ratio"],
            "volatility": df.iloc[idx]["volatility"],
        })
    return pd.DataFrame(events)


def main() -> None:
    all_events = []
    for pair in PAIRS:
        df = load_pair_data(pair)
        df = compute_features(df)
        events = generate_events(df, pair)
        all_events.append(events)
        print(f"{pair}: {len(events)} events")
    
    events = pd.concat(all_events, ignore_index=True)
    if len(events) < 20:
        raise RuntimeError(f"Too few events: {len(events)}")
    
    events["split"] = ["train"] * (len(events) // 2) + ["test"] * (len(events) - len(events) // 2)
    print(f"Total eventos: {len(events)}")
    
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
        experiment_id="EXP-002",
        events=events,
        hypothesis="H1-estructural-multi-par",
        tribunal_version="1.0",
        baseline_id="BASELINE-EDIFICIO",
        baseline_version="1.0",
        registry=registry,
        baseline_manager=baseline_manager,
        report_dir=REPORT_DIR,
        baseline_comparison=baseline_comparison,
    )

    if artifacts.gate_decision is None:
        raise RuntimeError("EXP-002 did not produce a gate decision")

    decision = artifacts.gate_decision
    evidence = artifacts.evidence_report
    robustness = artifacts.robustness_report

    print("\nExperimento: EXP-002")
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
