"""Unit tests for stochastic_zones (stoch_entry_help help layer)."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stochastic_zones import apply_stoch_help, zone_from_k


# ── R1/R2: zone boundaries ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "k, expected",
    [
        (0, "Z1"),
        (10, "Z1"),
        (20, "Z1"),
        (20.01, "Z2"),
        (40, "Z2"),
        (40.01, "Z3"),
        (60, "Z3"),
        (60.01, "Z4"),
        (79.99, "Z4"),
        (80, "Z5"),
        (100, "Z5"),
    ],
)
def test_zone_from_k_boundaries(k, expected):
    assert zone_from_k(k) == expected


def test_zone_from_k_clamps_below_zero():
    assert zone_from_k(-5) == "Z1"


def test_zone_from_k_clamps_above_100():
    assert zone_from_k(120) == "Z5"


def test_zone_from_k_none():
    assert zone_from_k(None) is None


# ── R3/R4/R6/R7: full CALL/PUT × soft/hard matrix ────────────────────────────

# (direction, zone_k, mode, action, score_delta)
_MATRIX = [
    # CALL soft
    ("CALL", 10, "soft", "BOOST", 10),   # Z1
    ("CALL", 30, "soft", "BOOST", 5),    # Z2
    ("CALL", 50, "soft", "PASS", 0),     # Z3
    ("CALL", 70, "soft", "PASS", 0),     # Z4
    ("CALL", 85, "soft", "PASS", 0),     # Z5 no veto soft
    # CALL hard
    ("CALL", 10, "hard", "BOOST", 10),
    ("CALL", 30, "hard", "BOOST", 5),
    ("CALL", 50, "hard", "PASS", 0),
    ("CALL", 70, "hard", "PASS", 0),
    ("CALL", 85, "hard", "VETO", 0),     # Z5 veto hard
    # PUT soft
    ("PUT", 10, "soft", "PASS", 0),      # Z1 no veto soft
    ("PUT", 30, "soft", "PASS", 0),      # Z2
    ("PUT", 50, "soft", "PASS", 0),      # Z3
    ("PUT", 70, "soft", "BOOST", 5),     # Z4
    ("PUT", 85, "soft", "BOOST", 10),    # Z5
    # PUT hard
    ("PUT", 10, "hard", "VETO", 0),      # Z1 veto hard
    ("PUT", 30, "hard", "PASS", 0),
    ("PUT", 50, "hard", "PASS", 0),
    ("PUT", 70, "hard", "BOOST", 5),
    ("PUT", 85, "hard", "BOOST", 10),
]


@pytest.mark.parametrize("direction,k,mode,action,delta", _MATRIX)
def test_apply_stoch_help_matrix(direction, k, mode, action, delta):
    res = apply_stoch_help(k, direction, mode)
    assert res.action == action
    assert res.score_delta == delta
    assert res.zone is not None
    if action == "VETO":
        assert res.reason == "stoch_extreme_against"
    elif action == "BOOST":
        assert res.reason == "stoch_boost"
        assert res.score_delta in (5, 10)
    else:
        assert res.reason == "stoch_pass"
        assert res.score_delta == 0


# ── R5: mode off ────────────────────────────────────────────────────────────

def test_mode_off_always_pass_with_zone():
    res = apply_stoch_help(85, "CALL", "off")
    assert res.action == "PASS"
    assert res.score_delta == 0
    assert res.zone == "Z5"
    assert res.reason == "stoch_pass"


def test_mode_off_put_extreme_no_veto():
    res = apply_stoch_help(10, "PUT", "off")
    assert res.action == "PASS"
    assert res.score_delta == 0
    assert res.zone == "Z1"


# ── R10: missing k ──────────────────────────────────────────────────────────

def test_k_none_pass_no_boost_no_veto():
    res = apply_stoch_help(None, "CALL", "hard")
    assert res.zone is None
    assert res.action == "PASS"
    assert res.score_delta == 0
    assert res.reason == "stoch_no_k"


# ── direction case-insensitive ──────────────────────────────────────────────

def test_direction_case_insensitive_call():
    upper = apply_stoch_help(10, "CALL", "hard")
    lower = apply_stoch_help(10, "call", "hard")
    assert upper == lower
    assert upper.action == "BOOST"
    assert upper.score_delta == 10


def test_direction_case_insensitive_put():
    upper = apply_stoch_help(85, "PUT", "hard")
    lower = apply_stoch_help(85, "put", "hard")
    assert upper == lower
    assert upper.action == "BOOST"
    assert upper.score_delta == 10


# ── unknown mode fail-safe off ──────────────────────────────────────────────

def test_unknown_mode_behaves_as_off():
    res = apply_stoch_help(85, "CALL", "banana")
    assert res.action == "PASS"
    assert res.score_delta == 0
    assert res.zone == "Z5"


# ── R9: cruce / divergencia not parameters ──────────────────────────────────

def test_apply_stoch_help_signature_has_no_cruce_or_divergencia():
    sig = inspect.signature(apply_stoch_help)
    params = set(sig.parameters)
    # V2: k_prev and d are keyword-only additions for cross-aware vetos.
    # Core params remain k/direction/mode. Old params must NOT return.
    assert {"k", "direction", "mode"}.issubset(params)
    assert "cruce" not in params
    assert "divergencia" not in params
    assert "contradicts" not in params
    # V2 keyword-only params must have defaults (backward-compatible)
    assert sig.parameters["k_prev"].default is None
    assert sig.parameters["d"].default is None


# ── R11/R16: config STOCH_HELP_MODE default + env override ───────────────────

def test_config_stoch_help_mode_default_hard(monkeypatch):
    """R11: without STOCH_HELP_MODE env, config defaults to hard."""
    import importlib
    import config as cfg

    monkeypatch.delenv("STOCH_HELP_MODE", raising=False)
    importlib.reload(cfg)
    assert cfg.STOCH_HELP_MODE == "hard"


@pytest.mark.parametrize("mode", ["soft", "off", "hard"])
def test_config_stoch_help_mode_env_override(monkeypatch, mode):
    """R16: STOCH_HELP_MODE env overrides config (easy disable / soft / hard)."""
    import importlib
    import config as cfg

    monkeypatch.setenv("STOCH_HELP_MODE", mode)
    importlib.reload(cfg)
    try:
        assert cfg.STOCH_HELP_MODE == mode
    finally:
        # Restore production default so later tests see hard on the module.
        monkeypatch.delenv("STOCH_HELP_MODE", raising=False)
        importlib.reload(cfg)
        assert cfg.STOCH_HELP_MODE == "hard"
