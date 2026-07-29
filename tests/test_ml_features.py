"""Tests for ml_features — feature extraction and validation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ml_features import FEATURE_NAMES, extract_features, extract_from_db_row, validate_features


# ── Helpers ──────────────────────────────────────────────────────────────────


def _full_strategy_json() -> dict:
    """Complete strategy_json mock with all fields populated."""
    return {
        "direction": "CALL",
        "payout": 87,
        "duration_sec": 600,
        "spring_margin": 0.0012,
        "stoch_m15": {
            "zone": "Z3",
        },
        "pattern_snapshot": {
            "math_quality": {
                "hurst": 0.65,
                "r_squared": 0.82,
                "angle_deg": 12.5,
                "squeeze": 0.003,
                "composite": 71.0,
            },
            "score_breakdown": {
                "compression": 15.0,
                "bounce": 28.0,
                "fractal": 30.0,
                "context": 20.0,
                "payout": 18.0,
                "stoch_help": 5.0,
            },
        },
    }


# ── Tests: extract_features ──────────────────────────────────────────────────


class TestExtractFeatures:
    """Extract features from complete and partial strategy_json."""

    def test_all_18_keys_present(self):
        """Output must contain exactly the 18 FEATURE_NAMES keys."""
        features = extract_features(_full_strategy_json())
        assert set(features.keys()) == set(FEATURE_NAMES)

    def test_math_quality_values(self):
        """Math features are extracted from pattern_snapshot.math_quality."""
        features = extract_features(_full_strategy_json())
        assert features["math_hurst"] == 0.65
        assert features["math_r_squared"] == 0.82
        assert features["math_angle_deg"] == 12.5
        assert features["math_squeeze"] == 0.003
        assert features["math_composite"] == 71.0

    def test_stochastic_values(self):
        """Stoch M15 zone is encoded; bullish/bearish cross are NOT hardcoded
        (the model discovers them from zone + OHLC geometry on its own)."""
        features = extract_features(_full_strategy_json())
        assert features["stoch_m15_zone"] == 3.0
        assert "stoch_bullish_cross" not in features
        assert "stoch_bearish_cross" not in features

    def test_spring_margin_extracted(self):
        """spring_margin comes from top-level key."""
        features = extract_features(_full_strategy_json())
        assert features["spring_margin"] == 0.0012

    def test_score_breakdown_values(self):
        """Score breakdown features match mock."""
        features = extract_features(_full_strategy_json())
        assert features["score_compression"] == 15.0
        assert features["score_bounce"] == 28.0
        assert features["score_fractal"] == 30.0
        assert features["score_context"] == 20.0
        assert features["score_payout"] == 18.0
        assert features["score_stoch_help"] == 5.0

    def test_direction_call(self):
        """CALL direction encodes to 1.0."""
        features = extract_features(_full_strategy_json())
        assert features["direction"] == 1.0

    def test_direction_put(self):
        """PUT direction encodes to 0.0."""
        sj = _full_strategy_json()
        sj["direction"] = "PUT"
        features = extract_features(sj)
        assert features["direction"] == 0.0

    def test_payout_and_duration(self):
        """Payout and duration_sec extracted as floats."""
        features = extract_features(_full_strategy_json())
        assert features["payout"] == 87.0
        assert features["duration_sec"] == 600.0


class TestMissingDataDefaults:
    """Missing or null fields should fall back to safe defaults."""

    def test_missing_math_quality_defaults(self):
        """Missing math_quality dict → default values."""
        sj = _full_strategy_json()
        del sj["pattern_snapshot"]["math_quality"]
        features = extract_features(sj)
        assert features["math_hurst"] == 0.5
        assert features["math_r_squared"] == 0.0
        assert features["math_angle_deg"] == 0.0
        assert features["math_squeeze"] == 0.0
        assert features["math_composite"] == 50.0

    def test_missing_stoch_defaults(self):
        """Missing stoch_m15 → stoch zones default to 0."""
        sj = _full_strategy_json()
        del sj["stoch_m15"]
        features = extract_features(sj)
        assert features["stoch_m15_zone"] == 0.0
        assert features["stoch_m5_zone"] == 0.0
        assert features["stoch_m1_zone"] == 0.0

    def test_null_spring_margin(self):
        """spring_margin=None → 0.0."""
        sj = _full_strategy_json()
        sj["spring_margin"] = None
        features = extract_features(sj)
        assert features["spring_margin"] == 0.0

    def test_missing_spring_margin(self):
        """spring_margin absent → 0.0."""
        sj = _full_strategy_json()
        del sj["spring_margin"]
        features = extract_features(sj)
        assert features["spring_margin"] == 0.0

    def test_missing_score_breakdown_defaults(self):
        """Missing score_breakdown → all zeros."""
        sj = _full_strategy_json()
        del sj["pattern_snapshot"]["score_breakdown"]
        features = extract_features(sj)
        assert features["score_compression"] == 0.0
        assert features["score_bounce"] == 0.0
        assert features["score_fractal"] == 0.0

    def test_empty_strategy_json(self):
        """Completely empty dict → default values, no crash."""
        features = extract_features({})
        assert set(features.keys()) == set(FEATURE_NAMES)
        assert features["math_hurst"] == 0.5
        assert features["direction"] == 0.0
        assert features["payout"] == 85.0

    def test_stoch_zone_encoded_no_hardcoded_cross(self):
        """Stoch zone is encoded; bullish/bearish cross are intentionally absent
        (the Entry Intelligence Agent discovers crosses from zone + geometry)."""
        sj = _full_strategy_json()
        sj["stoch_m15"] = {"zone": "Z2"}
        features = extract_features(sj)
        assert features["stoch_m15_zone"] == 2.0
        assert "stoch_bullish_cross" not in features
        assert "stoch_bearish_cross" not in features


# ── Tests: validate_features ─────────────────────────────────────────────────


class TestValidateFeatures:
    """validate_features checks all 18 fields exist and are numeric."""

    def test_valid_features(self):
        """Complete feature dict → True."""
        features = extract_features(_full_strategy_json())
        assert validate_features(features) is True

    def test_missing_key(self):
        """Missing one key → False."""
        features = extract_features(_full_strategy_json())
        del features["math_hurst"]
        assert validate_features(features) is False

    def test_non_numeric_value(self):
        """Non-numeric value → False."""
        features = extract_features(_full_strategy_json())
        features["payout"] = "eighty"  # type: ignore[assignment]
        assert validate_features(features) is False

    def test_empty_dict(self):
        """Empty dict → False."""
        assert validate_features({}) is False


# ── Tests: extract_from_db_row ───────────────────────────────────────────────


class TestExtractFromDbRow:
    """Extract features from a dict representing a DB row."""

    def test_db_row_with_json_string(self):
        """strategy_json as JSON string is parsed correctly."""
        import json
        sj = _full_strategy_json()
        row = {
            "strategy_json": json.dumps(sj),
            "spring_margin": 0.005,
        }
        features = extract_from_db_row(row)
        assert features["math_hurst"] == 0.65
        assert features["spring_margin"] == 0.005

    def test_db_row_with_dict(self):
        """strategy_json as dict (already deserialized)."""
        row = {
            "strategy_json": _full_strategy_json(),
            "spring_margin": None,
        }
        features = extract_from_db_row(row)
        assert features["math_hurst"] == 0.65

    def test_db_row_missing_strategy_json(self):
        """Missing strategy_json → defaults."""
        row = {"spring_margin": 0.1}
        features = extract_from_db_row(row)
        assert set(features.keys()) == set(FEATURE_NAMES)
        assert features["spring_margin"] == 0.1

    def test_db_row_invalid_json(self):
        """Malformed JSON string → defaults, no crash."""
        row = {"strategy_json": "{bad json", "spring_margin": 0.0}
        features = extract_from_db_row(row)
        assert set(features.keys()) == set(FEATURE_NAMES)

    def test_db_row_empty(self):
        """Empty row dict → defaults."""
        features = extract_from_db_row({})
        assert set(features.keys()) == set(FEATURE_NAMES)
