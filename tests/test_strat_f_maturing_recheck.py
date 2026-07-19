"""Tests para feature #16: re-chequeo M15 al promover desde maturing_watchlist.

Cubre R1-R5 del spec strat_f_maturing_m15_recheck.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import scanner as sc
from maturing_watchlist import MaturingWatchlist, MaturingEntry, make_key
from strat_fractal import recheck_m15_alignment, stoch_m5_exhausted
from models import ConsolidationZone


# ---------------------------------------------------------------------------
# R1 / R5 — recheck_m15_alignment (alineación actual, no la de detección)
# ---------------------------------------------------------------------------
def _candles_15m(close_trend: str):
    """Devuelve 15 velas M15 con tendencia: 'up' | 'down' | 'flat'."""
    base = 100.0
    closes = []
    for i in range(15):
        if close_trend == "up":
            closes.append(base + i)
        elif close_trend == "down":
            closes.append(base - i)
        else:
            closes.append(base)
    return [
        SimpleNamespace(ts=float(i), open=c, high=c + 1, low=c - 1, close=c)
        for i, c in enumerate(closes)
    ]


@pytest.mark.parametrize(
    "trend,direction,expected",
    [
        ("flat", "CALL", True),    # range -> alineado (R5)
        ("flat", "PUT", True),
        ("up", "CALL", True),     # M15 alcista + CALL = alineado
        ("down", "PUT", True),    # M15 bajista + PUT = alineado
        ("down", "CALL", False),  # R1/R2: contra-tendencia
        ("up", "PUT", False),     # R1/R2: contra-tendencia
    ],
)
def test_recheck_m15_alignment(trend, direction, expected):
    candles = _candles_15m(trend)
    assert recheck_m15_alignment(candles, direction) is expected


# ---------------------------------------------------------------------------
# R3 — stoch_m5_exhausted (confirmación de agotamiento del contra-movimiento)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "k,direction,expected",
    [
        (10.0, "CALL", True),    # CALL contra-M15-bajista + stoch<20 = agotado
        (50.0, "CALL", False),   # stoch neutro -> NO confirmado
        (90.0, "PUT", True),     # PUT contra-M15-alcista + stoch>80 = agotado
        (50.0, "PUT", False),
        (None, "CALL", False),   # sin dato -> NO confirmado
    ],
)
def test_stoch_m5_exhausted(k, direction, expected):
    assert stoch_m5_exhausted(k, direction) is expected


# ---------------------------------------------------------------------------
# R3 / R4 — integración: promover vs descartar en contra-tendencia
# ---------------------------------------------------------------------------
def _make_ctx(sym, f_eval, mw_entries):
    """Ctx mínimo para _evaluate_strat_f_serial con _eval_override.

    mw_entries: lista de MaturingEntry para simular la sala de espera activa.
    """
    candles = [SimpleNamespace(ts=float(i), open=100.0, high=101.0, low=99.0, close=100.0) for i in range(15)]
    candles_15m = _candles_15m("down")  # M15 bajista -> CALL es contra-tendencia
    candles_1m = [SimpleNamespace(ts=0.0, open=100.0, high=101.0, low=99.0, close=100.0)]
    ctx = SimpleNamespace(
        sym=sym,
        payout=90,
        candles_5m=list(candles),
        candles_1m=list(candles_1m),
        candles_15m=list(candles_15m),
        strat_f_only_mode=False,
        maturing_snapshot=list(mw_entries or []),
        initial_amount=2.0,
        session_id="test-session",
        bb_scan_id="test-scan",
        flags={"STRAT_A_ONLY": False, "STRAT_F_ENABLED": True, "MIN_PAYOUT": 80,
               "STOCH_HELP_MODE": "hard", "MATURING_WATCHLIST_MODE": "live"},
        _eval_override=f_eval,
    )
    return ctx


def _maturing_entry(sym, direction, band=98.0):
    return MaturingEntry(
        asset=sym, direction=direction, band=band, m15_context="range",
        m5_event="fractal_down", bars_age=5, payout=90,
        first_seen_ts=0.0, last_seen_ts=0.0, status="maturing",
    )


def _f_eval(direction, m15_ctx):
    zone = ConsolidationZone(
        asset="EURUSD_otc", ceiling=98.0, floor=98.0,
        bars_inside=10, detected_at=0.0, range_pct=0.002,
    )
    return SimpleNamespace(
        has_signal=True, direction=direction, m15_context=m15_ctx,
        m5_event="fractal_down", skip_reason=None, strength=0.7,
        pattern_name="fractal_down", zone=zone, spring_margin=0.0,
    )


def test_promote_against_trend_requires_stoch_exhausted():
    """R3/R4: CALL contra-M15-bajista solo promueve si stoch M5 < 20.

    Sin confirmación de agotamiento -> DROP (no operar).
    Con confirmación -> MARK_PROMOTED.
    """
    sym = "EURUSD_otc"
    f_eval = _f_eval("CALL", "downtrend")  # contra-tendencia
    entry = _maturing_entry(sym, "CALL")
    key = entry.key

    # Caso A: stoch M5 neutro (k=50) -> debe DESCARTAR (drop)
    ctx = _make_ctx(sym, f_eval, [entry])
    with patch("stochastic_m15.compute_stoch", return_value={"k": 50.0}):
        with patch.object(sc, "recheck_m15_alignment", return_value=False):
            res = sc._evaluate_strat_f_serial(ctx)
    ops = res.maturing_ops
    assert ("drop", (key, "contra_tendencia_sin_agotamiento_stoch")) in ops, ops
    assert ("mark_promoted", (key, "live")) not in ops, ops
    assert res.f_candidate is None, "no debe crearse candidato si se descarta"

    # Caso B: stoch M5 agotado (k=10 < 20) -> debe PROMOVER
    ctx2 = _make_ctx(sym, f_eval, [entry])
    with patch("stochastic_m15.compute_stoch", return_value={"k": 10.0}):
        with patch.object(sc, "recheck_m15_alignment", return_value=False):
            res2 = sc._evaluate_strat_f_serial(ctx2)
    ops2 = res2.maturing_ops
    assert ("mark_promoted", (key, "live")) in ops2, ops2
    assert ("drop", (key, "contra_tendencia_sin_agotamiento_stoch")) not in ops2, ops2
    assert res2.f_candidate is not None


def test_aligned_trend_promotes_without_stoch():
    """R5: tendencia alineada promueve sin exigir stoch."""
    sym = "EURUSD_otc"
    f_eval = _f_eval("CALL", "range")  # range -> alineado
    entry = _maturing_entry(sym, "CALL")
    key = entry.key
    ctx = _make_ctx(sym, f_eval, [entry])
    with patch("stochastic_m15.compute_stoch", return_value={"k": 50.0}):
        with patch.object(sc, "recheck_m15_alignment", return_value=True):
            res = sc._evaluate_strat_f_serial(ctx)
    ops = res.maturing_ops
    assert ("mark_promoted", (key, "live")) in ops, ops
    assert [o for o in ops if o[0] == "drop"] == [], ops
