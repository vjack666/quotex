"""Tests for ml_scorer — MLScorer predict, save/load, fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import joblib
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ml_features import FEATURE_NAMES
from ml_scorer import MLScorer


# ── Helpers ──────────────────────────────────────────────────────────────────


class _FakeLGBModel:
    """Picklable stub that mimics LightGBM classifier API."""

    def __init__(self, return_proba: float = 0.72) -> None:
        self._return_proba = return_proba
        self.feature_importances_ = [10.0 + i for i in range(len(FEATURE_NAMES))]
        self.feature_name_ = list(FEATURE_NAMES)

    def predict_proba(self, X):
        return [[1.0 - self._return_proba, self._return_proba]]

    def predict(self, X):
        return [1 if self._return_proba >= 0.5 else 0]


def _mock_lgb_model(return_proba: float = 0.72) -> _FakeLGBModel:
    """Create a fake LightGBM model that returns a fixed probability."""
    return _FakeLGBModel(return_proba)


def _full_features() -> dict[str, float]:
    """Complete feature dict with realistic values."""
    return {
        "math_hurst": 0.65,
        "math_r_squared": 0.82,
        "math_angle_deg": 12.5,
        "math_squeeze": 0.003,
        "math_composite": 71.0,
        "stoch_zone": 3.0,
        "stoch_score_delta": 3.0,
        "stoch_bullish_cross": 1.0,
        "stoch_bearish_cross": 0.0,
        "spring_margin": 0.0012,
        "score_compression": 15.0,
        "score_bounce": 28.0,
        "score_fractal": 30.0,
        "score_context": 20.0,
        "score_payout": 18.0,
        "score_stoch_help": 5.0,
        "direction": 1.0,
        "payout": 87.0,
        "duration_sec": 600.0,
    }


def _save_mock_model(path: Path, model: Any, meta: dict | None = None) -> None:
    """Persist a mock model to disk via joblib."""
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "meta": meta or {}}, str(path))


# ── Tests: predict with mock model ───────────────────────────────────────────


class TestPredict:
    """Predict returns confidence 0-1 when model is loaded."""

    def test_predict_returns_confidence(self):
        """predict() returns a float between 0 and 1."""
        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = _mock_lgb_model(0.72)
        scorer._meta = {}

        result = scorer.predict(_full_features())
        assert result is not None
        assert 0.0 <= result <= 1.0
        assert result == pytest.approx(0.72)

    def test_predict_clamps_boundary(self):
        """Confidence is clamped to [0, 1]."""
        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = _mock_lgb_model(1.05)  # absurd probability
        scorer._meta = {}

        result = scorer.predict(_full_features())
        assert result == 1.0

    def test_predict_empty_features(self):
        """Empty features dict → None."""
        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = _mock_lgb_model()
        scorer._meta = {}

        assert scorer.predict({}) is None

    def test_predict_exception_returns_none(self):
        """If predict_proba raises, predict returns None."""
        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = MagicMock()
        scorer._model.predict_proba.side_effect = RuntimeError("boom")
        scorer._meta = {}

        result = scorer.predict(_full_features())
        assert result is None


# ── Tests: fallback when no model file ──────────────────────────────────────


class TestFallback:
    """When no model file exists, scorer is unavailable."""

    def test_no_model_file(self):
        """Missing model file → is_available False, predict returns None."""
        scorer = MLScorer(model_path="/nonexistent/path/model.pkl")
        assert scorer.is_available() is False
        assert scorer.predict(_full_features()) is None

    def test_feature_importance_empty_when_no_model(self):
        """No model → feature_importance returns empty dict."""
        scorer = MLScorer(model_path="/nonexistent/path/model.pkl")
        assert scorer.feature_importance() == {}


# ── Tests: is_available states ──────────────────────────────────────────────


class TestIsAvailable:
    """is_available reflects model load state."""

    def test_available_after_manual_load(self):
        """After loading a valid model file, is_available is True."""
        mock_model = _mock_lgb_model()
        tmp = Path("/tmp/test_ml_scorer_available.pkl")
        _save_mock_model(tmp, mock_model)

        scorer = MLScorer(model_path=str(tmp))
        assert scorer.is_available() is True

        tmp.unlink(missing_ok=True)

    def test_unavailable_after_corrupt_load(self):
        """Corrupt file → is_available is False."""
        tmp = Path("/tmp/test_ml_scorer_corrupt.pkl")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(b"not a valid joblib file")

        scorer = MLScorer(model_path=str(tmp))
        assert scorer.is_available() is False

        tmp.unlink(missing_ok=True)


# ── Tests: save / load round-trip ───────────────────────────────────────────


class TestSaveLoad:
    """Save and load persist the model correctly."""

    def test_save_load_round_trip(self, tmp_path: Path):
        """Saved model can be reloaded and produces same prediction."""
        model_path = tmp_path / "model.pkl"
        mock_model = _mock_lgb_model(0.68)

        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = model_path
        scorer._model = mock_model
        scorer._meta = {"trained_at": "2024-06-01", "f1": 0.75}

        scorer.save(str(model_path))
        assert model_path.exists()

        scorer2 = MLScorer(model_path=str(model_path))
        assert scorer2.is_available() is True
        result = scorer2.predict(_full_features())
        assert result == pytest.approx(0.68)
        assert scorer2._meta["f1"] == 0.75

    def test_load_returns_false_on_missing(self):
        """load() returns False for non-existent file."""
        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = None
        scorer._meta = {}

        assert scorer.load("/nonexistent/path.pkl") is False
        assert scorer.is_available() is False


# ── Tests: feature_importance ───────────────────────────────────────────────


class TestFeatureImportance:
    """feature_importance maps feature names to importances."""

    def test_importance_with_mock_model(self):
        """Returns a dict mapping all 18 features to float importances."""
        mock_model = _mock_lgb_model()
        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = mock_model
        scorer._meta = {}

        imp = scorer.feature_importance()
        assert set(imp.keys()) == set(FEATURE_NAMES)
        for v in imp.values():
            assert isinstance(v, float)
            assert v >= 0.0

    def test_importance_empty_dict_on_exception(self):
        """If model.feature_importances_ fails → empty dict."""

        class _BadModel:
            def __getattr__(self, name):
                raise AttributeError("no importances")

        scorer = MLScorer.__new__(MLScorer)
        scorer.model_path = Path("dummy")
        scorer._model = _BadModel()
        scorer._meta = {}

        assert scorer.feature_importance() == {}
