"""Test de regresión (2026-07-27): la señal STRAT-F fresca debe propagar su
fuerza (strength 0-1) a f_candidate.score (0-100) para que select_best no la
rechace por score bajo (bug que dejaba 0 disparos en DEMO real).

Ruta fresca: fractal detectado en el ciclo, SIN maturing_watchlist activa.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import scanner as sc  # noqa: E402
from models import ConsolidationZone  # noqa: E402


def _candles(close=100.0):
    return [SimpleNamespace(ts=float(i), open=close, high=close + 1,
                            low=close - 1, close=close) for i in range(15)]


def _f_eval(strength, direction="CALL", m15_ctx="range"):
    zone = ConsolidationZone(
        asset="EURUSD_otc", ceiling=98.0, floor=98.0,
        bars_inside=10, detected_at=0.0, range_pct=0.002,
    )
    return SimpleNamespace(
        has_signal=True, direction=direction, m15_context=m15_ctx,
        m5_event="fractal_down", skip_reason=None, strength=strength,
        pattern_name="fractal_down", zone=zone, spring_margin=0.0,
        math_quality=0.5, decision=None,
    )


def _make_ctx_fresh(sym, f_eval):
    candles_15m = _candles(100.0)  # range -> alineado
    ctx = SimpleNamespace(
        sym=sym,
        payout=90,
        candles_5m=list(_candles()),
        candles_1m=[SimpleNamespace(ts=0.0, open=100.0, high=101.0,
                                     low=99.0, close=100.0)],
        candles_15m=list(candles_15m),
        strat_f_only_mode=True,
        maturing_snapshot=[],  # ruta FRESCA: sin sala de espera
        initial_amount=2.0,
        session_id="test-session",
        bb_scan_id="test-scan",
        flags={"STRAT_A_ONLY": False, "STRAT_F_ENABLED": True, "MIN_PAYOUT": 80,
               "STOCH_HELP_MODE": "hard", "MATURING_WATCHLIST_MODE": "live"},
        _eval_override=f_eval,
    )
    return ctx


def _make_scanner():
    # _evaluate_strat_f_serial es función de módulo (scanner._evaluate_strat_f_serial)
    return sc


def test_fresh_strat_f_propagates_strength_to_score():
    """La señal fresca aceptada debe tener f_candidate.score == strength*100."""
    f_eval = _f_eval(strength=0.69)  # 69 en 0-100
    ctx = _make_ctx_fresh("EURUSD_otc", f_eval)
    res = sc._evaluate_strat_f_serial(ctx)
    assert res.f_candidate is not None, "señal fresca debe crear candidato"
    assert res.strat_f_accepts == 1
    # BUG fijo: el score del candidato debe reflejar la fuerza STRAT-F.
    assert res.f_candidate.score == 69.0, (
        f"score no propagado: {res.f_candidate.score} != 69.0 (strength*100)"
    )


def test_fresh_strat_f_passes_select_best():
    """Con score 69 (> STRAT_F_MIN_SCORE=60) select_best debe aceptarlo."""
    from entry_scorer import select_best
    from config import STRAT_F_MIN_SCORE

    f_eval = _f_eval(strength=0.69)
    ctx = _make_ctx_fresh("EURUSD_otc", f_eval)
    res = sc._evaluate_strat_f_serial(ctx)
    cand = res.f_candidate
    assert cand.score >= STRAT_F_MIN_SCORE
    selected, rejected = select_best(
        [cand], threshold=STRAT_F_MIN_SCORE,
        threshold_for=lambda c: STRAT_F_MIN_SCORE,
    )
    assert len(selected) == 1, f"select_best rechazó la señal: {rejected}"
    assert selected[0] is cand
