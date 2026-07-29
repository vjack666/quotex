"""LightGBM scoring wrapper — predict confidence 0-1 or fallback to None."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import joblib

from ml_features import FEATURE_NAMES

# Import the training pipeline lazily-friendly (script lives in scripts/).
import os as _os
import sys as _sys

_SCRIPTS_DIR = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts"
)
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

try:
    from train_lightgbm import run_training
except Exception:  # pragma: no cover - only when run outside repo layout
    run_training = None  # type: ignore[assignment]

_MIN_TRADES_DEFAULT = 500
_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models"
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = os.path.join(_MODELS_DIR, "lightgbm_v1.pkl")


class MLScorer:
    """Wrapper around a trained LightGBM classifier.

    Loads a persisted model from disk and exposes a simple predict API.
    When the model file does not exist or cannot be loaded, predict()
    gracefully returns None so the static scoring pipeline continues.
    """

    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH) -> None:
        """Initialize scorer, attempting to load model from disk.

        Args:
            model_path: Path to the joblib-serialized model file.
        """
        self.model_path = Path(model_path)
        self._model: Any = None
        self._meta: dict[str, Any] = {}
        self.load(str(self.model_path))

    def _n_features(self) -> int | None:
        """Expected feature count of the loaded booster, or None if unknown."""
        try:
            m = self._model
            if m is None:
                return None
            if hasattr(m, "booster_") and m.booster_ is not None:
                return int(m.booster_.num_feature())
            if hasattr(m, "n_features_"):
                return int(m.n_features_)
        except Exception:
            return None
        return None

    def predict(self, features: dict[str, float]) -> float | None:
        """Return confidence 0.0-1.0 for a single candidate, or None.

        Crash-proof by design: a schema/feature-count mismatch or any
        prediction failure degrades to None (static scoring continues).
        The live bot must never break because of the ML layer.
        """
        if not self.is_available():
            return None
        if not features:
            return None
        # Guard: code vs model feature-count mismatch → skip, never call lightgbm.
        expected = self._n_features()
        if expected is not None and len(FEATURE_NAMES) != expected:
            logger.error(
                "[ML] feature-count mismatch (code=%d, model=%d) — skipping predict",
                len(FEATURE_NAMES),
                expected,
            )
            return None
        try:
            import pandas as pd

            row = pd.DataFrame(
                [[features.get(name, 0.0) for name in FEATURE_NAMES]],
                columns=FEATURE_NAMES,
            )
            proba = self._model.predict_proba(row)[0]
            # Class index 1 = WIN; return probability of winning
            confidence = float(proba[1])
            return max(0.0, min(1.0, confidence))
        except Exception:
            logger.exception("[ML] predict failed")
            return None

    def is_available(self) -> bool:
        """True if a trained model is loaded in memory."""
        return self._model is not None

    def save(self, path: str) -> None:
        """Persist the model and metadata to disk via joblib.

        Args:
            path: Destination file path (overwrites if exists).
        """
        payload = {"model": self._model, "meta": self._meta}
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(payload, str(dest))
        logger.info("[ML] model saved to %s", dest)

    def load(self, path: str) -> bool:
        """Load a model from disk.

        Args:
            path: Source file path.

        Returns:
            True if loaded successfully, False otherwise.
        """
        src = Path(path)
        if not src.exists():
            return False
        try:
            payload = joblib.load(str(src))
            self._model = payload.get("model")
            self._meta = payload.get("meta", {})
            self.model_path = src
            return True
        except Exception:
            logger.exception("[ML] failed to load model from %s", src)
            self._model = None
            self._meta = {}
            return False

    def feature_importance(self) -> dict[str, float]:
        """Return a feature-name → importance mapping.

        If no model is loaded, returns an empty dict.
        """
        if not self.is_available():
            return {}
        try:
            raw = self._model.feature_importances_
            names = self._model.feature_name_ or FEATURE_NAMES
            return {name: float(imp) for name, imp in zip(names, raw)}
        except Exception:
            logger.exception("[ML] feature_importance failed")
            return {}

    # ── Training (Feature 18 — T6/T8) ───────────────────────────────────────
    def train(
        self,
        db_paths: list[str] | None = None,
        min_trades: int = _MIN_TRADES_DEFAULT,
        force: bool = False,
    ) -> dict[str, Any]:
        """Entrena el modelo LightGBM del Entry Intelligence Agent.

        Delegates to the standalone pipeline in ``scripts/train_lightgbm.py``.
        Fuente PREFERIDA (T10/T11, Feature 27): la memoria única del
        Experience Engine (``data/market_memory/``); si está vacía, el
        pipeline cae a las DBs legacy (scan_candidates / trade_journal).
        The pipeline enforces a minimum-sample guard (default 500 resolved
        trades). If the guard blocks training, returns a dict with
        ``trained=False`` and the ``missing`` count; no model is written.

        On success it reloads the freshly trained model into memory and
        returns the metadata dict (``trained=True``).

        Args:
            db_paths: Optional explicit list of DB paths (defaults to auto-discovery).
            min_trades: Minimum resolved trades required to train.
            force: Bypass the guard (NOT recommended).

        Returns:
            Metadata dict with at least ``trained`` (bool).
        """
        if run_training is None:
            logger.error("[ML] training pipeline unavailable (train_lightgbm import failed)")
            return {"trained": False, "error": "pipeline_import_failed"}

        result = run_training(
            db_paths=db_paths,
            model_path=str(self.model_path),
            meta_path=os.path.join(_MODELS_DIR, "lightgbm_meta.json"),
            min_trades=min_trades,
            force=force,
        )
        if result.get("trained"):
            # Reload so predict() uses the new model immediately.
            self.load(str(self.model_path))
        return result
