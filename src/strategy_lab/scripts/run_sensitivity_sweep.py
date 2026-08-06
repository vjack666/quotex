"""EXP-037: Sensibilidad de secuencia — barrido de configs de acceso a piso.

Barre una matriz chica sobre el dataset offline y registra cada corrida.
Objetivo: encontrar la config que maximice ENTRADA sin llenar de ruido.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sequence_engine import SequenceCard, SequenceEngine

DATASET_PATH = PROJECT_ROOT / "data/exports/exp037_kd_distance_dataset.csv"


@dataclass(frozen=True)
class SweepConfig:
    kd_distance: float = 2.0
    dwell_cerebro: int = 1
    cross_limpieza_ok: bool = True


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_offline_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise SystemExit(f"missing dataset: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    df = df.sort_values("ts").reset_index(drop=True)
    df["kd_distance"] = df["kd_distance"].apply(lambda v: _safe_float(v))
    return df


def evaluate_candidate(row: pd.Series, config: SweepConfig) -> Dict[str, Any]:
    engine = SequenceEngine(
        min_dwell_ticks={
            "RECEPCION": 1,
            "CEREBRO": config.dwell_cerebro,
            "ENTRADA": 0,
        },
        min_kd_distance=float(config.kd_distance),
    )
    # offline dataset no trae payout/brake_ok/extreme_ok; usamos defaults
    # para aislar el impacto de kd_distance/dwell/cross_clean.
    features = {
        "payout": 90,
        "brake_ok": True,
        "extreme_ok": True,
        "cross_ok": True,
        "cross_limpieza_ok": config.cross_limpieza_ok,
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
    reject_reason = None
    if card.history:
        last = card.history[-1]
        reject_reason = getattr(last, "reject_reason", None)
    return {
        "id": int(row.name),
        "final_floor": card.current_floor,
        "reject_reason": reject_reason,
        "reached_entrada": card.current_floor == "ENTRADA",
        "reject_reception": any(getattr(t, "reject_reason", None) == "RECHAZAR_RECEPCION" for t in card.history),
        "reject_cerebro": any(getattr(t, "reject_reason", None) == "RECHAZAR_CEREBRO" for t in card.history),
        "stuck_cerebro": any(getattr(t, "reject_reason", None) == "DWELL_CEREBRO" for t in card.history),
    }


def run_config(df: pd.DataFrame, config: SweepConfig) -> Dict[str, Any]:
    results = [evaluate_candidate(row, config) for _, row in df.iterrows()]
    reached_entrada = [r for r in results if r["reached_entrada"]]
    reject_reception = sum(1 for r in results if r["reject_reception"])
    reject_cerebro = sum(1 for r in results if r["reject_cerebro"])
    stuck_cerebro = sum(1 for r in results if r["stuck_cerebro"])
    fail_entrada = len(results) - len(reached_entrada)
    reject_reason_counts: Dict[str, int] = {}
    for r in results:
        reason = r.get("reject_reason")
        if reason:
            reject_reason_counts[reason] = reject_reason_counts.get(reason, 0) + 1
    return {
        "config": config.__dict__,
        "total": len(results),
        "reached_entrada": len(reached_entrada),
        "fail_entrada": fail_entrada,
        "reject_reception": reject_reception,
        "reject_cerebro": reject_cerebro,
        "stuck_cerebro": stuck_cerebro,
        "reject_reason_counts": reject_reason_counts,
        "entrada_rate": len(reached_entrada) / len(results) if results else 0.0,
        "noise_rate": (reject_reception + reject_cerebro + stuck_cerebro) / len(results) if results else 0.0,
    }


def build_matrix() -> List[SweepConfig]:
    configs = []
    for kd in [0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
        for dwell in [0, 1, 2]:
            for cross_clean in [True, False]:
                configs.append(SweepConfig(kd_distance=kd, dwell_cerebro=dwell, cross_limpieza_ok=cross_clean))
    return configs


def main() -> int:
    df = load_offline_dataset()
    matrix = build_matrix()
    rows = []
    for config in matrix:
        result = run_config(df, config)
        rows.append(result)
        print(
            f"kd={config.kd_distance} dwell={config.dwell_cerebro} cross_clean={config.cross_limpieza_ok} "
            f"=> entrada={result['reached_entrada']} rate={result['entrada_rate']:.3f}"
        )
    ranked = sorted(rows, key=lambda r: (r["entrada_rate"], -r["noise_rate"]), reverse=True)
    out_path = PROJECT_ROOT / "src/strategy_lab/results/exp037_sensitivity_sweep.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"ranked": ranked}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTop config: {ranked[0]['config']}")
    print(f"  entrada={ranked[0]['reached_entrada']} rate={ranked[0]['entrada_rate']:.3f}")
    print(f"  noise_rate={ranked[0]['noise_rate']:.3f}")
    print(f"Results: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
