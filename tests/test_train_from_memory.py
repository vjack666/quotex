"""T10/T11 Experience Engine — retrain del Entry Intelligence Agent desde
la memoria única (data/market_memory/) en vez de scan_candidates.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for p in (str(SRC), str(SCRIPTS), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import train_lightgbm as train  # noqa: E402
from ml_features import FEATURE_NAMES, extract_features_full  # noqa: E402

MEMORY_ROOT = ROOT / "data" / "market_memory"

pytestmark = pytest.mark.skipif(
    not MEMORY_ROOT.exists() or not list(MEMORY_ROOT.glob("*.jsonl")),
    reason="memoria única no poblada (data/market_memory/ vacío)",
)

EXPECTED_ROW_KEYS = {
    "candles_1m", "candles_5m", "candles_15m",
    "stoch_m15", "stoch_m5", "stoch_m1",
    "direction", "payout", "duration_sec", "asset", "ts",
    "order_result", "profit", "entry_price", "exit_price",
    "loss_reason", "strategy_details",
}


class TestLoadExperiencesAsRows:
    def test_reads_closed_experiences_from_real_memory(self):
        rows = train.load_experiences_as_rows(str(MEMORY_ROOT))
        # La memoria real sembrada tiene 211 experiencias cerradas.
        assert len(rows) >= 200
        for r in rows:
            assert r["source"] == "market_memory"
            assert r["target"] in (0, 1)
            assert set(r["features"].keys()) == set(FEATURE_NAMES)

    def test_row_shape_matches_extract_features_full_contract(self):
        # Reconstruir el row intermedio como lo hace load_experiences_as_rows
        # y verificar que extract_features_full lo consume sin lanzar.
        from experience_engine import ExperienceMemory

        exps = ExperienceMemory(root=MEMORY_ROOT).all_experiences()
        closed = [e for e in exps if e.is_closed()]
        assert closed
        e = closed[0]
        row = {
            "candles_1m": e.raw.get("candles_1m"),
            "candles_5m": e.raw.get("candles_5m"),
            "candles_15m": e.raw.get("candles_15m"),
            "stoch_m15": e.contexto_previo.get("stoch_m15"),
            "stoch_m5": e.contexto_previo.get("stoch_m5"),
            "stoch_m1": e.contexto_previo.get("stoch_m1"),
            "direction": e.evento.get("direccion"),
            "payout": e.evento.get("payout"),
            "duration_sec": e.evento.get("duration_sec"),
            "asset": e.asset,
            "ts": e.ts,
            "order_result": e.resultado.get("decision"),
            "profit": e.resultado.get("profit"),
            "entry_price": e.evento.get("nivel"),
            "exit_price": e.resultado.get("exit_price"),
            "loss_reason": e.resultado.get("loss_reason"),
            "strategy_details": None,
        }
        assert set(row.keys()) == EXPECTED_ROW_KEYS
        feats = extract_features_full(row)  # no debe lanzar
        assert set(feats.keys()) == set(FEATURE_NAMES)
        assert len(feats) == len(FEATURE_NAMES)
        for v in feats.values():
            assert isinstance(v, (int, float))

    def test_missing_memory_returns_empty(self, tmp_path):
        assert train.load_experiences_as_rows(str(tmp_path / "nada")) == []


class TestRunTrainingFromMemory:
    def test_trains_model_from_real_memory(self, tmp_path):
        model_file = tmp_path / "models" / "lightgbm_tmp.pkl"
        meta_file = tmp_path / "models" / "lightgbm_tmp_meta.json"
        result = train.run_training(
            db_paths=None,
            model_path=str(model_file),
            meta_path=str(meta_file),
            min_trades=1,
            quiet=True,
            mem_root=str(MEMORY_ROOT),
        )
        assert result["trained"] is True
        assert result["n_trades"] >= 200
        assert os.path.exists(model_file)
        assert os.path.exists(meta_file)
        # F1 se calcula (float, aunque el modelo sea débil temprano)
        assert isinstance(result["metrics"]["f1"], float)
        assert set(result["feature_names"]) == set(FEATURE_NAMES)
