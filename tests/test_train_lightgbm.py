"""Tests for scripts/train_lightgbm.py — Feature 18 training pipeline (T9).

These tests run ONLY the new modules (no bot/server), offline, and never
collect data. They exercise:
  (a) the 500-trade guard blocks training on a small synthetic DB,
  (b) feature extraction returns exactly the 18 features on real DB rows,
  (c) with a sufficiently large synthetic dataset, training runs and
      persists data/models/lightgbm_v1.pkl + lightgbm_meta.json.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for p in (str(SRC), str(SCRIPTS), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ml_features import FEATURE_NAMES, extract_features  # noqa: E402


# ── Load the training module by path (avoids package assumptions) ──────────
def _load_train_module():
    spec = importlib.util.spec_from_file_location(
        "train_lightgbm", str(SCRIPTS / "train_lightgbm.py")
    )
    assert spec is not None and spec.loader is not None, "train_lightgbm spec failed"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


train = _load_train_module()


# ── Synthetic DB helpers ────────────────────────────────────────────────────
def _make_strategy_json(win: bool, seed: int) -> dict:
    """Deterministic synthetic strategy_json with a learnable signal.

    WINS correlate with higher math_composite / score_fractal; LOSSES with
    lower values. Good enough for the pipeline to fit a non-trivial model.
    """
    base = 0.5 + (seed % 7) * 0.01
    if win:
        comp = 70.0 + (seed % 20)
        frac = 30.0 + (seed % 10)
        zone = (seed % 5) + 1
    else:
        comp = 30.0 + (seed % 20)
        frac = 5.0 + (seed % 10)
        zone = (seed % 3) + 1
    return {
        "direction": "CALL" if win else "PUT",
        "payout": 90.0,
        "duration_sec": 300.0,
        "spring_margin": 0.01 * (seed % 5),
        "stoch_m15": {
            "zone": f"Z{zone}",
            "score_delta": float(seed % 5),
            "action": "bullish_cross" if win else "bearish_cross",
        },
        "pattern_snapshot": {
            "math_quality": {
                "hurst": base + 0.1,
                "r_squared": base,
                "angle_deg": 10.0 + (seed % 15),
                "squeeze": 0.002,
                "composite": comp,
            },
            "score_breakdown": {
                "compression": 10.0,
                "bounce": 20.0,
                "fractal": frac,
                "context": 15.0,
                "payout": 18.0,
                "stoch_help": 4.0,
            },
        },
    }


def _write_candidates_db(path: Path, n_resolved: int, win_rate: float = 0.6) -> None:
    """Create a trade_journal-style DB with `n_resolved` STRAT-F rows."""
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE candidates (
            id INTEGER PRIMARY KEY,
            scanned_at TEXT,
            outcome TEXT,
            strategy_origin TEXT,
            strategy_json TEXT,
            spring_margin REAL,
            direction TEXT,
            payout REAL,
            ticket_duration_sec REAL,
            entry_duration_sec REAL
        )
        """
    )
    import json as _json
    for i in range(n_resolved):
        win = (i % 100) < int(win_rate * 100)
        sj = _make_strategy_json(win, i)
        cur.execute(
            "INSERT INTO candidates (scanned_at, outcome, strategy_origin, "
            "strategy_json, spring_margin, direction, payout, ticket_duration_sec, "
            "entry_duration_sec) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                f"2026-07-1{i % 9 + 1} 12:{i % 60:02d}:00",
                "WIN" if win else "LOSS",
                "STRAT-F",
                _json.dumps(sj),
                0.01 * (i % 5),
                sj["direction"],
                90.0,
                300.0,
                300.0,
            ),
        )
    conn.commit()
    conn.close()


# ── (a) Guard blocks training on small dataset ─────────────────────────────
class TestGuardSmallDataset:
    def test_guard_blocks_under_500(self, tmp_path: Path):
        db = tmp_path / "trade_journal-2026-07-99.db"
        _write_candidates_db(db, n_resolved=50)  # well below 500

        model_file = tmp_path / "models" / "lightgbm_v1.pkl"
        meta_file = tmp_path / "models" / "lightgbm_meta.json"

        result = train.run_training(
            db_paths=[str(db)],
            model_path=str(model_file),
            meta_path=str(meta_file),
            min_trades=500,
            quiet=True,
        )
        assert result["trained"] is False
        assert result["actual"] == 50
        assert result["missing"] == 450
        # No files written
        assert not model_file.exists()
        assert not meta_file.exists()

    def test_guard_message_format(self, tmp_path: Path, capsys):
        db = tmp_path / "trade_journal-2026-07-99.db"
        _write_candidates_db(db, n_resolved=50)
        result = train.run_training(
            db_paths=[str(db)],
            model_path=str(tmp_path / "m.pkl"),
            meta_path=str(tmp_path / "meta.json"),
            min_trades=500,
            quiet=False,
        )
        out = capsys.readouterr().out
        assert "Faltan 450 trades para entrenar" in out or "Faltan 450 trades para entrenar" in result.get("message", "")
        assert result["trained"] is False


# ── (b) Feature extraction returns the 18 features ─────────────────────────
class TestFeatureExtraction:
    def test_real_db_rows_yield_18_features(self, tmp_path: Path):
        db = tmp_path / "trade_journal-2026-07-99.db"
        _write_candidates_db(db, n_resolved=30)
        rows = train.load_resolved_trades(db_paths=[str(db)])
        assert len(rows) == 30
        n_feat = len(FEATURE_NAMES)
        for r in rows:
            feats = r["features"]
            # NOTE: the code defines 19 features (stoch_bullish_cross AND
            # stoch_bearish_cross are both present); FEATURE_NAMES is the
            # source of truth and extract_features matches it exactly.
            assert set(feats.keys()) == set(FEATURE_NAMES)
            assert len(feats) == n_feat
            # numeric
            for v in feats.values():
                assert isinstance(v, (int, float))

    def test_extract_features_contract(self):
        feats = extract_features(_make_strategy_json(True, 7))
        assert set(feats.keys()) == set(FEATURE_NAMES)
        assert len(feats) == len(FEATURE_NAMES)

    def test_load_resolved_only_wins_losses(self, tmp_path: Path):
        db = tmp_path / "trade_journal-2026-07-99.db"
        _write_candidates_db(db, n_resolved=40)
        # add a pending (non-resolved) row that must be ignored
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO candidates (scanned_at, outcome, strategy_origin, "
            "strategy_json, spring_margin, direction, payout) VALUES (?,?,?,?,?,?,?)",
            ("2026-07-20 12:00:00", "PENDING", "STRAT-F", "{}", 0.0, "CALL", 90.0),
        )
        conn.commit()
        conn.close()
        rows = train.load_resolved_trades(db_paths=[str(db)])
        assert len(rows) == 40


# ── (c) Large synthetic dataset trains and saves model ─────────────────────
class TestTrainSufficientData:
    def test_train_and_save_with_large_dataset(self, tmp_path: Path):
        db = tmp_path / "trade_journal-2026-07-99.db"
        _write_candidates_db(db, n_resolved=600)  # >= 500

        model_file = tmp_path / "models" / "lightgbm_v1.pkl"
        meta_file = tmp_path / "models" / "lightgbm_meta.json"

        result = train.run_training(
            db_paths=[str(db)],
            model_path=str(model_file),
            meta_path=str(meta_file),
            min_trades=500,
            quiet=True,
        )
        assert result["trained"] is True
        assert result["n_trades"] == 600
        assert os.path.exists(model_file)
        assert os.path.exists(meta_file)

        # meta.json content
        with open(meta_file, encoding="utf-8") as fh:
            meta = json.load(fh)
        assert meta["trained"] is True
        assert set(meta["feature_names"]) == set(FEATURE_NAMES)
        assert len(meta["feature_importances"]) == len(FEATURE_NAMES)
        for k in ("accuracy", "precision", "recall", "f1"):
            assert k in meta["metrics"]

        # The saved model is loadable via MLScorer
        sys.path.insert(0, str(SRC))
        from ml_scorer import MLScorer

        scorer = MLScorer(model_path=str(model_file))
        assert scorer.is_available() is True
        feats = extract_features(_make_strategy_json(True, 3))
        conf = scorer.predict(feats)
        assert conf is not None
        assert 0.0 <= conf <= 1.0

    def test_force_bypasses_guard(self, tmp_path: Path):
        db = tmp_path / "trade_journal-2026-07-99.db"
        _write_candidates_db(db, n_resolved=50)
        model_file = tmp_path / "models" / "lightgbm_v1.pkl"
        meta_file = tmp_path / "models" / "lightgbm_meta.json"
        result = train.run_training(
            db_paths=[str(db)],
            model_path=str(model_file),
            meta_path=str(meta_file),
            min_trades=500,
            force=True,
            quiet=True,
        )
        # force must train even with <500
        assert result["trained"] is True
        assert os.path.exists(model_file)
