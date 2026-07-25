"""Unit tests for stochastic_zones (V3: agotamiento verdadero).

V3 reemplaza el BOOST ciego en zonas extremas por la regla de
agotamiento confirmado (ver stoch_exhaustion). Sin datos de cruce/vela,
Z1 CALL y Z5 PUT devuelven PASS (EXHAUST_WAIT), no BOOST. Con cruce
confirmado + vela de rechazo en la franja S/R devuelven BOOST 12.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stochastic_zones import apply_stoch_help, zone_from_k
from stochastic_m15 import compute_stoch


# ── zone boundaries (sin cambios) ─────────────────────────────────────────


@pytest.mark.parametrize(
    "k, expected",
    [
        (0, "Z1"), (10, "Z1"), (20, "Z1"), (20.01, "Z2"), (40, "Z2"),
        (40.01, "Z3"), (60, "Z3"), (60.01, "Z4"), (79.99, "Z4"),
        (80, "Z5"), (100, "Z5"),
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


# ── V3: matriz SIN datos de cruce/vela ─────────────────────────────────────
# Z1 CALL y Z5 PUT sin datos -> PASS (EXHAUST_WAIT), no BOOST.
# Zonas medias igual que antes. Contra-direccion en hard -> VETO.

_MATRIX_NO_DATA = [
    # CALL
    ("CALL", 10, "soft", "PASS", 0),   # Z1 sin datos -> WAIT
    ("CALL", 30, "soft", "BOOST", 5),  # Z2
    ("CALL", 50, "soft", "PASS", 0),   # Z3
    ("CALL", 70, "soft", "PASS", 0),   # Z4
    ("CALL", 85, "soft", "PASS", 0),   # Z5 sin datos -> WAIT
    ("CALL", 10, "hard", "PASS", 0),   # Z1 sin datos -> WAIT
    ("CALL", 30, "hard", "BOOST", 5),
    ("CALL", 50, "hard", "PASS", 0),
    ("CALL", 70, "hard", "PASS", 0),
    ("CALL", 85, "hard", "VETO", 0),    # Z5 contra-direccion -> VETO hard
    # PUT
    ("PUT", 10, "soft", "PASS", 0),     # Z1 contra -> sin datos PASS
    ("PUT", 30, "soft", "PASS", 0),     # Z2
    ("PUT", 50, "soft", "PASS", 0),     # Z3
    ("PUT", 70, "soft", "BOOST", 5),    # Z4 a favor
    ("PUT", 85, "soft", "PASS", 0),     # Z5 sin datos -> WAIT
    ("PUT", 10, "hard", "VETO", 0),     # Z1 contra -> VETO hard
    ("PUT", 30, "hard", "PASS", 0),
    ("PUT", 50, "hard", "PASS", 0),
    ("PUT", 70, "hard", "BOOST", 5),
    ("PUT", 85, "hard", "PASS", 0),     # Z5 sin datos -> WAIT
]


@pytest.mark.parametrize("direction,k,mode,action,delta", _MATRIX_NO_DATA)
def test_apply_stoch_help_matrix_no_data(direction, k, mode, action, delta):
    res = apply_stoch_help(k, direction, mode)
    assert res.action == action
    assert res.score_delta == delta
    assert res.zone is not None
    if action == "VETO":
        assert res.reason == "stoch_extreme_against"
    elif action == "BOOST":
        assert res.reason == "stoch_boost"
        assert res.score_delta in (5, 10, 12)
    else:
        # PASS: puede ser stoch_pass (zonas medias) o stoch_exhaust_wait (extremo)
        assert res.reason.startswith(("stoch_pass", "stoch_exhaust_wait"))


# ── V3: agotamiento CONFIRMADO -> BOOST 12 ─────────────────────────────────

def _make_stoch_put_exhausted():
    """%K en Z5 con cruce bajista confirmado hace 1 vela M15."""
    k = [60.0, 95.0, 90.0, 88.0]
    d = [72.0, 85.0, 98.0, 70.0]
    st = {
        "k": 88.0, "d": 70.0, "estado": "SOBRECOMPRA",
        "cruce": "bajista", "k_prev": 90.0,
        "cross_ago": 1, "k_vals": k, "d_vals": d,
    }
    return st


def _make_stoch_call_exhausted():
    """%K en Z1 con cruce alcista confirmado hace 1 vela M15."""
    k = [20.0, 18.0, 25.0, 15.0]
    d = [22.0, 22.0, 21.0, 30.0]
    st = {
        "k": 15.0, "d": 30.0, "estado": "SOBREVENTA",
        "cruce": "alcista", "k_prev": 25.0,
        "cross_ago": 1, "k_vals": k, "d_vals": d,
    }
    return st


class _C:
    def __init__(self, o, h, l, c):
        self.open, self.high, self.low, self.close = o, h, l, c


def test_put_z5_exhaust_confirmed_boost12():
    st = _make_stoch_put_exhausted()
    # estrella fugaz PUT en resistencia 1.0040 (zona alrededor)
    candles = [_C(1.0005, 1.0040, 1.0003, 1.0006)]
    res = apply_stoch_help(88.0, "PUT", "hard", stoch_full=st,
                           candles_15m=candles, zone_lo=1.0037, zone_hi=1.0043)
    assert res.action == "BOOST"
    assert res.score_delta == 12
    assert res.reason == "stoch_exhaust_confirmed"


def test_call_z1_exhaust_confirmed_boost12():
    st = _make_stoch_call_exhausted()
    # martillo CALL en soporte 0.99935 (zona alrededor)
    candles = [_C(1.0000, 1.00035, 0.99935, 1.0003)]
    res = apply_stoch_help(15.0, "CALL", "hard", stoch_full=st,
                           candles_15m=candles, zone_lo=0.99905, zone_hi=0.99965)
    assert res.action == "BOOST"
    assert res.score_delta == 12
    assert res.reason == "stoch_exhaust_confirmed"


def test_put_z5_exhaust_wait_no_cruce():
    # Z5, k=94.5, k_prev=100: recien entra, SIN cruce (caso AUDUSD id 142)
    st = {"k": 94.5, "d": 83.9, "k_prev": 100.0,
          "k_vals": [80.0, 90.0, 100.0, 94.5],
          "d_vals": [83.0, 83.5, 83.9, 83.9]}
    res = apply_stoch_help(94.5, "PUT", "hard", stoch_full=st,
                           candles_15m=[_C(1.0000, 1.0030, 1.0001, 1.0028)],
                           zone_lo=0.9997, zone_hi=1.0003)
    assert res.action == "PASS"
    assert res.reason.startswith("stoch_exhaust_wait")


# ── mode off ──────────────────────────────────────────────────────────────

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


# ── missing k ────────────────────────────────────────────────────────────

def test_k_none_pass_no_boost_no_veto():
    res = apply_stoch_help(None, "CALL", "hard")
    assert res.zone is None
    assert res.action == "PASS"
    assert res.score_delta == 0
    assert res.reason == "stoch_no_k"


# ── direction case-insensitive ────────────────────────────────────────────

def test_direction_case_insensitive_call():
    upper = apply_stoch_help(10, "CALL", "hard")
    lower = apply_stoch_help(10, "call", "hard")
    assert upper == lower
    # Z1 CALL sin datos -> PASS (EXHAUST_WAIT) en V3
    assert upper.action == "PASS"


def test_direction_case_insensitive_put():
    upper = apply_stoch_help(85, "PUT", "hard")
    lower = apply_stoch_help(85, "put", "hard")
    assert upper == lower
    # Z5 PUT sin datos -> PASS (EXHAUST_WAIT) en V3
    assert upper.action == "PASS"


# ── unknown mode fail-safe off ────────────────────────────────────────────

def test_unknown_mode_behaves_as_off():
    res = apply_stoch_help(85, "CALL", "banana")
    assert res.action == "PASS"
    assert res.score_delta == 0
    assert res.zone == "Z5"


# ── V3 signature ──────────────────────────────────────────────────────────

def test_apply_stoch_help_signature_has_exhaust_params():
    sig = inspect.signature(apply_stoch_help)
    params = set(sig.parameters)
    assert {"k", "direction", "mode"}.issubset(params)
    assert "cruce" not in params
    assert "divergencia" not in params
    assert "contradicts" not in params
    # V3 keyword-only params for exhaustion detection (backward-compatible defaults)
    assert sig.parameters["k_prev"].default is None
    assert sig.parameters["d"].default is None
    assert sig.parameters["stoch_full"].default is None
    assert sig.parameters["candles_15m"].default is None
    assert sig.parameters["zone_lo"].default is None
    assert sig.parameters["zone_hi"].default is None
    assert sig.parameters["stoch_m5"].default is None
    assert sig.parameters["zone_strength"].default is None
    assert sig.parameters["candles_1m"].default is None
    assert sig.parameters["lookback"].default == 3


# ── config STOCH_HELP_MODE default + env override ─────────────────────────

def test_config_stoch_help_mode_default_hard(monkeypatch):
    import importlib
    import config as cfg
    monkeypatch.delenv("STOCH_HELP_MODE", raising=False)
    importlib.reload(cfg)
    assert cfg.STOCH_HELP_MODE == "hard"


@pytest.mark.parametrize("mode", ["soft", "off", "hard"])
def test_config_stoch_help_mode_env_override(monkeypatch, mode):
    import importlib
    import config as cfg
    monkeypatch.setenv("STOCH_HELP_MODE", mode)
    importlib.reload(cfg)
    try:
        assert cfg.STOCH_HELP_MODE == mode
    finally:
        monkeypatch.delenv("STOCH_HELP_MODE", raising=False)
        importlib.reload(cfg)
        assert cfg.STOCH_HELP_MODE == "hard"


def test_apply_stoch_help_zone_strength_primario():
    """R7 endurecido vía apply_stoch_help: zone_strength alto ensancha la
    banda => vela 'casi' en la zona cuenta (CONFIRMADO). Sin el (None)
    la misma vela queda fuera => WAIT. Verifica que el dato zone_strength
    encaja en apply_stoch_help y llega a evaluate_exhaustion."""
    st = _make_stoch_put_exhausted()
    candle = _C(1.0005, 1.0045, 1.0003, 1.0006)
    res_none = apply_stoch_help(
        88.0, "PUT", "hard", stoch_full=st,
        candles_15m=[candle], zone_lo=1.0037, zone_hi=1.0043,
        zone_strength=None,
    )
    res_zs = apply_stoch_help(
        88.0, "PUT", "hard", stoch_full=st,
        candles_15m=[candle], zone_lo=1.0037, zone_hi=1.0043,
        zone_strength=0.90,
    )
    assert res_none.action == "PASS"
    assert res_zs.action == "BOOST"
    assert res_zs.score_delta == 12


def test_apply_stoch_help_camino_atrapado():
    """R4-bis: stoch atrapado en extremo (sin vela de rechazo) es
    condicion de entrada valida, no requiere ruptura."""
    st = {
        "k": 92.0, "d": 88.0,
        "k_vals": [95.0, 85.0, 82.0, 85.0, 90.0, 92.0],
        "d_vals": [90.0, 88.0, 80.0, 82.0, 86.0, 88.0],
    }
    candles = [_C(1.0000, 1.0030, 1.0001, 1.0028)]
    res = apply_stoch_help(
        92.0, "PUT", "hard", stoch_full=st,
        candles_15m=candles, zone_lo=0.9997, zone_hi=1.0003,
    )
    assert res.action == "BOOST"
    assert res.score_delta == 12
    assert res.reason == "stoch_exhaust_confirmed"
