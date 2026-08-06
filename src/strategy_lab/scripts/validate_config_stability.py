"""EXP-038: Valida estabilidad temporal de la config ganadora de EXP-037.

Split temporal:
- train: primeros 70% del dataset offline
- test: últimos 30%

Métrica:
- entrada_rate en train vs test
- Si delta < 5% => estable
- Si delta >= 5% => inestable, no convertir en default

Uso:
    python src/strategy_lab/scripts/validate_config_stability.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sequence_engine import SequenceCard, SequenceEngine

DATASET_PATH = PROJECT_ROOT / "data/exports/exp037_kd_distance_dataset.csv"
RESULTS_PATH = PROJECT_ROOT / "src/strategy_lab/results/exp038_config_stability.json"

# Config ganadora de EXP-037 (más restrictiva que kd=0.0)
WINNING_CONFIG = {
    "kd_distance": 2.0,
    "dwell_cerebro": 1,
    "cross_limpieza_ok": True,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise SystemExit(f"missing dataset: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    df = df.sort_values("ts").reset_index(drop=True)
    df["kd_distance"] = df["kd_distance"].apply(lambda v: _safe_float(v))
    return df


def evaluate_split(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    engine = SequenceEngine(
        min_dwell_ticks={
            "RECEPCION": 1,
            "CEREBRO": int(config["dwell_cerebro"]),
            "ENTRADA": 0,
        },
        min_kd_distance=float(config["kd_distance"]),
    )
    results = []
    for _, row in df.iterrows():
        features = {
            "payout": 90,
            "brake_ok": True,
            "extreme_ok": True,
            "cross_ok": True,
            "cross_limpieza_ok": bool(config["cross_limpieza_ok"]),
            "kd_distance": _safe_float(row.get("kd_distance"), default=0.0),
        }
        card = SequenceCard(
            hypothesis_id=f"OFFLINE-{int(row.name)}",
            asset=str(row.get("ts", "")),
            direction=str(row.get("direction", "")),
        )
        engine.evaluate(card, features, timestamp=str(row.get("ts")))
        card.tick()
        engine.evaluate(card, features, timestamp=str(row.get("ts")))
        results.append(card.current_floor == "ENTRADA")
    entrada_count = sum(1 for r in results if r)
    return {
        "total": len(results),
        "entrada_count": entrada_count,
        "entrada_rate": entrada_count / len(results) if results else 0.0,
    }


def main() -> int:
    df = load_dataset()
    split_idx = int(len(df) * 0.7)
    train_df = df.iloc[:split_idx].reset_index(drop=True)
    test_df = df.iloc[split_idx:].reset_index(drop=True)

    train_result = evaluate_split(train_df, WINNING_CONFIG)
    test_result = evaluate_split(test_df, WINNING_CONFIG)

    delta = abs(train_result["entrada_rate"] - test_result["entrada_rate"])
    stable = delta < 0.05

    report = {
        "config": WINNING_CONFIG,
        "train": train_result,
        "test": test_result,
        "delta": delta,
        "stable": stable,
        "conclusion": "ESTABLE" if stable else "INESTABLE",
    }

    RESULTS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if stable else 1


if __name__ == "__main__":
    raise SystemExit(main())
