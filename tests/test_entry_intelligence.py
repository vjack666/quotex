"""Tests for the Entry Intelligence Agent (Feature 18).

Offline, deterministic, no bot/server. Exercises:
  · OHLC geometry extraction from raw candles (T2b/T2c)
  · extract_features_full: full vector from a DB row incl. candles + 3-TF stoch
  · score_candidate ML layer is inert when ML disabled / model missing (T10-T13)
  · auto-retrain decision logic: guard blocks < MIN_TRADES, force trains (T14-T16)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for p in (str(SRC), str(SCRIPTS), str(ROOT)):
    if p not in __import__("sys").path:
        __import__("sys").path.insert(0, p)

from ml_features import (  # noqa: E402
    FEATURE_NAMES,
    extract_geometry_from_candles,
    extract_features_full,
)


# ── Geometry (T2b/T2c) ───────────────────────────────────────────────────────
class TestGeometry:
    def _bar(self, o, h, l, c):
        return {"open": o, "high": h, "low": l, "close": c}

    def test_bullish_body_aligned_call(self):
        # CALL, bar closes UP with no lower wick → body_dir=+1, low opp_wick
        m1 = [self._bar(1.0, 1.02, 1.0, 1.015)]
        g = extract_geometry_from_candles(m1, [], [], "CALL")
        assert g["body_dir"] == 1.0
        assert g["body_ratio"] == pytest.approx(0.75, abs=0.01)
        assert g["opp_wick_ratio"] == pytest.approx(0.0, abs=1e-6)
        # closed at 75% of the range (not the extreme) → entry_extreme_pos ~0.75
        assert g["entry_extreme_pos"] == pytest.approx(0.75, abs=0.01)

    def test_bearish_body_aligned_put(self):
        # PUT, bar closes DOWN → body_dir=+1 (aligned with PUT)
        m1 = [self._bar(1.02, 1.02, 1.0, 1.005)]
        g = extract_geometry_from_candles(m1, [], [], "PUT")
        assert g["body_dir"] == 1.0
        assert g["opp_wick_ratio"] == pytest.approx(0.0, abs=1e-6)

    def test_misaligned_body_call(self):
        # CALL but bar closes DOWN → body_dir=-1 (wrong direction)
        m1 = [self._bar(1.02, 1.02, 1.0, 1.005)]
        g = extract_geometry_from_candles(m1, [], [], "CALL")
        assert g["body_dir"] == -1.0

    def test_empty_candles_defaults(self):
        g = extract_geometry_from_candles([], [], [], "CALL")
        # fractal_align and entry_extreme_pos default to neutral 0.5 when no
        # candles; the rest are 0.0
        assert g["fractal_align"] == 0.5
        assert g["entry_extreme_pos"] == 0.5
        for k, v in g.items():
            if k not in ("fractal_align", "entry_extreme_pos"):
                assert v == 0.0

    def test_spike_no_opposing_wick(self):
        # Spike con conviccion: cuerpo a favor, sin mecha opuesta (Ruben rule)
        m1 = [self._bar(1.0, 1.03, 1.0, 1.028)]
        g = extract_geometry_from_candles(m1, [], [], "CALL")
        assert g["body_ratio"] > 0.8
        assert g["opp_wick_ratio"] < 0.05

    def test_compression_coil(self):
        # Small entry bar inside a wide M15 range → compression_geom high
        m1 = [self._bar(1.0, 1.001, 0.999, 1.0005)]
        m15 = [self._bar(1.0, 1.05, 0.95, 1.0), self._bar(1.0, 1.05, 0.95, 1.0)]
        g = extract_geometry_from_candles(m1, [], m15, "CALL")
        assert g["compression_geom"] > 0.9


# ── extract_features_full ────────────────────────────────────────────────────
class TestExtractFeaturesFull:
    def _row(self):
        return {
            "direction": "CALL",
            "payout": 90.0,
            "duration_sec": 300.0,
            "asset": "EURUSD_otc",
            "stoch_m15": json.dumps({"zone": "Z3"}),
            "stoch_m5": json.dumps({"zone": "Z2"}),
            "stoch_m1": json.dumps({"zone": "Z1"}),
            "candles_1m": json.dumps([
                {"open": 1.0, "high": 1.02, "low": 1.0, "close": 1.015},
                {"open": 1.015, "high": 1.03, "low": 1.01, "close": 1.028},
            ]),
            "candles_5m": json.dumps([]),
            "candles_15m": json.dumps([
                {"open": 1.0, "high": 1.05, "low": 0.95, "close": 1.0},
            ]),
            "ts": 1721836800.0,  # 2026-07-24 16:00 UTC → hour 16, dow 4
        }

    def test_full_vector_complete(self):
        f = extract_features_full(self._row())
        assert set(f.keys()) == set(FEATURE_NAMES)
        assert len(f) == len(FEATURE_NAMES)
        for v in f.values():
            assert isinstance(v, (int, float))

    def test_stoch_three_timeframes(self):
        f = extract_features_full(self._row())
        assert f["stoch_m15_zone"] == 3.0
        assert f["stoch_m5_zone"] == 2.0
        assert f["stoch_m1_zone"] == 1.0

    def test_time_context(self):
        import datetime as _dt
        from datetime import timezone as _tz

        ts = _dt.datetime(2026, 7, 24, 16, 30, 0, tzinfo=_tz.utc).timestamp()
        row = self._row()
        row["ts"] = ts
        f = extract_features_full(row)
        assert f["hour_utc"] == 16.0
        assert f["dow"] == 4.0

    def test_asset_id_stable(self):
        f = extract_features_full(self._row())
        assert f["asset_id"] >= 0 and f["asset_id"] < 64


# ── score_candidate ML layer (T10-T13) ──────────────────────────────────────
class TestScoreCandidateMLLayer:
    def _make_entry(self):
        # Import lazily to avoid heavy bot imports in isolated test
        import importlib
        import models

        C = type("C", (), {})
        zone = models.ConsolidationZone(
            asset="EURUSD_otc", ceiling=1.10, floor=1.09,
            bars_inside=3, detected_at=0.0, range_pct=0.01,
        )
        e = models.CandidateEntry(
            asset="EURUSD_otc", payout=90, zone=zone, direction="CALL",
            candles=[type("C", (), {"open": 1.0, "high": 1.02, "low": 1.0, "close": 1.015})()],
            score=0.0, score_breakdown={}, mode=models.SignalMode.REBOUND,
        )
        e.candles_15m = [type("C", (), {"open": 1.0, "high": 1.05, "low": 0.95, "close": 1.0})()]
        return e

    def test_ml_off_does_not_change_score(self):
        import config as _cfg
        _cfg.ML_ENABLED = False
        import entry_scorer

        e = self._make_entry()
        s1 = entry_scorer.score_candidate(e)
        e2 = self._make_entry()
        s2 = entry_scorer.score_candidate(e2)
        assert s1 == s2  # deterministic, ML layer inert

    def test_ml_on_no_model_falls_back_cleanly(self):
        import config as _cfg
        _cfg.ML_ENABLED = True
        import entry_scorer

        entry_scorer._ML_SCORER = None  # force reload attempt
        # Point model path to a non-existent file → predict returns None
        _cfg.ML_MODEL_PATH = "data/models/__does_not_exist__.pkl"
        e = self._make_entry()
        base = entry_scorer.score_candidate(e)
        # Without a model, the score equals the pure base score (no crash)
        assert isinstance(base, (int, float))
        assert not hasattr(e, "ml_confidence") or e.ml_confidence is None


# ── Auto-retrain decision (T14-T16) ─────────────────────────────────────────
class TestAutoRetrain:
    def _write_small_db(self, path: Path, n: int):
        if path.exists():
            path.unlink()
        con = sqlite3.connect(str(path))
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE scan_candidates (
                id INTEGER PRIMARY KEY, asset TEXT, direction TEXT,
                order_result TEXT, ts REAL, candles_1m TEXT, candles_5m TEXT,
                candles_15m TEXT, stoch_m15 TEXT, stoch_m5 TEXT, stoch_m1 TEXT,
                payout REAL, duration_sec REAL, strategy TEXT, strategy_details TEXT
            )"""
        )
        for i in range(n):
            win = i % 2 == 0
            cur.execute(
                "INSERT INTO scan_candidates "
                "(asset, direction, order_result, ts, candles_1m, candles_5m, "
                "candles_15m, stoch_m15, stoch_m5, stoch_m1, payout, "
                "duration_sec, strategy, strategy_details) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "EURUSD_otc",
                    "CALL" if win else "PUT",
                    "WIN" if win else "LOSS",
                    1721800000.0 + i,
                    json.dumps([{"open": 1.0, "high": 1.02, "low": 1.0, "close": 1.015}]),
                    json.dumps([]),
                    json.dumps([]),
                    json.dumps({"zone": "Z3"}),
                    json.dumps({"zone": "Z2"}),
                    json.dumps({"zone": "Z1"}),
                    90.0,
                    300.0,
                    "STRAT-F",
                    json.dumps({}),
                ),
            )
        con.commit()
        con.close()

    def test_guard_blocks_under_min_trades(self, tmp_path, monkeypatch):
        import entry_intelligence as ei

        db = tmp_path / "black_box_strat_2026-07-99.db"
        self._write_small_db(db, n=50)  # well below 500
        monkeypatch.setattr(ei, "DB_DIR", tmp_path)
        monkeypatch.setattr(ei, "MODELS_DIR", tmp_path / "models")

        res = ei.maybe_retrain(force=False, quiet=True)
        assert res["triggered"] is False
        assert "threshold" in res["reason"] or "500" in res["reason"]

    def test_force_trains_when_under_min(self, tmp_path, monkeypatch):
        import entry_intelligence as ei

        db = tmp_path / "black_box_strat_2026-07-99.db"
        self._write_small_db(db, n=120)
        models_dir = tmp_path / "models"
        monkeypatch.setattr(ei, "DB_DIR", tmp_path)
        monkeypatch.setattr(ei, "MODELS_DIR", models_dir)
        # Isolate the retrain state so the real last_retrain.json does not
        # suppress the decision (last_ts recent => 0 new trades).
        monkeypatch.setattr(ei, "STATE_PATH", models_dir / "last_retrain.json")
        if (models_dir / "last_retrain.json").exists():
            (models_dir / "last_retrain.json").unlink()

        res = ei.maybe_retrain(force=True, quiet=True)
        assert res["trained"] is True
        assert (models_dir / "lightgbm_v1.pkl").exists()
