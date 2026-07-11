"""Tests de STRAT-F (Fractal / Wyckoff, marco M15/M5/M1)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import Candle  # noqa: E402
from strat_fractal import evaluate_strat_f  # noqa: E402


def _c(ts: int, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=c)


def _ct(ts: int, o: float, h: float, l: float, c: float, ticks: int = 0) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=c, ticks=ticks)


def _flat_15m(n=8, base=1.10000) -> list[Candle]:
    """M15 en rango plano (contexto 'range')."""
    out = []
    for i in range(n):
        out.append(_c(1000 + i * 900, base, base + 0.0002, base - 0.0002, base))
    return out


def _broken_15m(n=8, base=1.10000) -> list[Candle]:
    """M15 con ruptura al alza con cuerpo (contexto 'broken')."""
    out = []
    for i in range(n - 1):
        out.append(_c(1000 + i * 900, base, base + 0.0002, base - 0.0002, base))
    last = out[-1]
    out.append(_c(1000 + (n - 1) * 900, last.close, last.close + 0.002, last.close, last.close + 0.002))
    return out


def _downtrend_15m(n=8, base=1.10000) -> list[Candle]:
    out = []
    p = base
    for i in range(n):
        c = p - 0.001
        out.append(_c(1000 + i * 900, p, p + 0.0002, c - 0.0002, c))
        p = c
    return out


def _fractal_down_5m(band: float = 1.09900) -> list[Candle]:
    """M5 con fractal bajista (suelo) en el índice 4, rodeado de velas mayores."""
    out = [
        _c(2000, 1.10000, 1.10050, 1.09980, 1.10020),
        _c(2300, 1.10020, 1.10060, 1.09990, 1.10030),
        _c(2600, 1.10030, 1.10040, 1.09995, 1.10010),
        _c(2900, 1.10010, 1.10020, band + 0.00030, band + 0.00010),  # no es el mínimo
        _c(3200, band + 0.00010, band + 0.00020, band, band + 0.00010),  # mínimo central (fractal down)
        _c(3500, band + 0.00010, band + 0.00040, band + 0.00005, band + 0.00030),
        _c(3800, band + 0.00030, band + 0.00050, band + 0.00020, band + 0.00040),
        _c(4100, band + 0.00040, band + 0.00060, band + 0.00030, band + 0.00050),
    ]
    return out


def _fractal_up_5m(band: float = 1.10100) -> list[Candle]:
    """M5 con fractal alcista (techo) en el índice 4."""
    out = [
        _c(2000, 1.10000, 1.10020, 1.09980, 1.10000),
        _c(2300, 1.10000, 1.10030, 1.09990, 1.10010),
        _c(2600, 1.10010, 1.10040, 1.09995, 1.10020),
        _c(2900, 1.10020, band - 0.00010, band - 0.00030, band - 0.00010),
        _c(3200, band - 0.00010, band, band - 0.00020, band - 0.00010),  # máximo central (fractal up)
        _c(3500, band - 0.00010, band - 0.00005, band - 0.00040, band - 0.00030),
        _c(3800, band - 0.00030, band - 0.00020, band - 0.00050, band - 0.00040),
        _c(4100, band - 0.00040, band - 0.00030, band - 0.00060, band - 0.00050),
    ]
    return out


def _m1_reject_low(band: float = 1.09900) -> list[Candle]:
    """M1 cuya última vela toca el suelo y cierra ARRIBA (rechazo alcista)."""
    return [
        _c(5000, 1.10000, 1.10010, 1.09990, 1.10000),
        _c(5060, band + 0.00020, band + 0.00030, band - 0.00005, band + 0.00010),  # toca y cierra arriba
    ]


def _m1_reject_high(band: float = 1.10100) -> list[Candle]:
    """M1 cuya última vela toca el techo y cierra ABAJO (rechazo bajista)."""
    return [
        _c(5000, 1.10000, 1.10010, 1.09990, 1.10000),
        _c(5060, band - 0.00005, band + 0.00030, band - 0.00010, band - 0.00010),  # toca y cierra abajo
    ]


def _m1_close_outside_low(band: float = 1.09900) -> list[Candle]:
    """M1 cuya última vela cierra POR DEBAJO del suelo (no rechaza)."""
    return [
        _c(5000, 1.10000, 1.10010, 1.09990, 1.10000),
        _c(5060, band + 0.00010, band + 0.00020, band - 0.00030, band - 0.00020),
    ]


# ── Casos ──

def test_fractal_down_range_m1_reject_returns_call():
    ev = evaluate_strat_f(
        _flat_15m(),
        _fractal_down_5m(),
        _m1_reject_low(),
        payout=85,
    )
    assert ev.has_signal is True
    assert ev.direction == "CALL"
    assert ev.pattern_name == "fractal_down"
    assert ev.confirms is True
    assert ev.m15_context == "range"


def test_fractal_up_range_m1_reject_returns_put():
    ev = evaluate_strat_f(
        _flat_15m(),
        _fractal_up_5m(),
        _m1_reject_high(),
        payout=85,
    )
    assert ev.has_signal is True
    assert ev.direction == "PUT"
    assert ev.pattern_name == "fractal_up"


def test_m15_broken_skips():
    ev = evaluate_strat_f(
        _broken_15m(),
        _fractal_down_5m(),
        _m1_reject_low(),
        payout=85,
    )
    assert ev.has_signal is False
    assert "roto" in (ev.skip_reason or "")


def test_call_against_downtrend_m15_skips():
    ev = evaluate_strat_f(
        _downtrend_15m(),
        _fractal_down_5m(),
        _m1_reject_low(),
        payout=85,
    )
    assert ev.has_signal is False
    assert "tendencia" in (ev.skip_reason or "")


def test_m1_closes_outside_skips():
    ev = evaluate_strat_f(
        _flat_15m(),
        _fractal_down_5m(),
        _m1_close_outside_low(),
        payout=85,
    )
    assert ev.has_signal is False
    assert "rechaza" in (ev.skip_reason or "")


def test_no_fractal_5m_skips():
    # M5 sin fractal (todas velas casi iguales y crecientes)
    flat_5m = [_c(2000 + i * 300, 1.10000 + i * 0.0001, 1.10020 + i * 0.0001, 1.09990 + i * 0.0001, 1.10000 + i * 0.0001) for i in range(8)]
    ev = evaluate_strat_f(_flat_15m(), flat_5m, _m1_reject_low(), payout=85)
    assert ev.has_signal is False
    assert ev.m5_event == "none"


def test_insufficient_5m_skips():
    ev = evaluate_strat_f(_flat_15m(), _fractal_down_5m()[:3], _m1_reject_low(), payout=85)
    assert ev.has_signal is False


def test_strength_higher_in_range():
    ev = evaluate_strat_f(_flat_15m(), _fractal_down_5m(), _m1_reject_low(), payout=85)
    assert ev.strength >= 0.7


def _flat_15m_with_ticks(n=8, base=1.10000, avg=100) -> list[Candle]:
    """M15 plano pero CON ticks (para que la Fase A pueda evaluar)."""
    return [_ct(1000 + i * 900, base, base + 0.0002, base - 0.0002, base, ticks=avg) for i in range(n)]


def _phase_a_15m() -> list[Candle]:
    """M15 con climax de venta (cuerpo grande + ticks altos) y absorcion luego."""
    base = 1.10000
    out = [_ct(1000 + i * 900, base, base + 0.0002, base - 0.0002, base, ticks=100) for i in range(5)]
    # Climax de venta: cuerpo grande (baja) + ticks altos
    out.append(_ct(1000 + 5 * 900, base, base + 0.0002, base - 0.0030, base - 0.0028, ticks=300))
    # Absorcion: cuerpos pequeños y pocos ticks
    out.append(_ct(1000 + 6 * 900, base - 0.0028, base - 0.0026, base - 0.0030, base - 0.0027, ticks=40))
    out.append(_ct(1000 + 7 * 900, base - 0.0027, base - 0.0025, base - 0.0029, base - 0.0028, ticks=35))
    return out


def test_phase_a_detected_with_ticks():
    from strat_fractal import _phase_a_from_ticks
    assert _phase_a_from_ticks(_phase_a_15m(), "CALL") is True


def test_phase_a_skipped_when_no_ticks():
    from strat_fractal import _phase_a_from_ticks
    assert _phase_a_from_ticks(_flat_15m(), "CALL") is False


def test_phase_a_strength_boost():
    ev_plain = evaluate_strat_f(_flat_15m_with_ticks(), _fractal_down_5m(), _m1_reject_low(), payout=85)
    ev_phase_a = evaluate_strat_f(_phase_a_15m(), _fractal_down_5m(), _m1_reject_low(), payout=85)
    assert ev_plain.has_signal is True
    assert ev_phase_a.has_signal is True
    assert ev_phase_a.strength > ev_plain.strength


# ── Filtros de calidad (SDD strat_f_quality_validation) ──────────────────

def test_r2_payout_bajo_rechaza():
    """R2 — payout < minimo -> rechazo sin evaluar."""
    ev = evaluate_strat_f(_flat_15m(), _fractal_down_5m(), _m1_reject_low(), payout=70, min_payout=80)
    assert ev.has_signal is False
    assert "payout" in (ev.skip_reason or "")


def test_r3_zona_joven_rechaza():
    """R3 — fractal demasiado reciente (edad < zone_min_age) -> rechazo."""
    # Fractal down en idx 5 -> bars_since_fractal = (8-1)-5 = 2 < 3 (zona joven)
    band = 1.09900
    m5 = [
        _c(2000, 1.10000, 1.10050, 1.09980, 1.10020),
        _c(2300, 1.10020, 1.10060, 1.09990, 1.10030),
        _c(2600, 1.10030, 1.10040, 1.09995, 1.10010),
        _c(2900, 1.10010, 1.10030, band + 0.00050, band + 0.00040),  # idx3
        _c(3200, band + 0.00040, band + 0.00050, band + 0.00030, band + 0.00035),  # idx4
        _c(3500, band + 0.00035, band + 0.00040, band, band + 0.00010),  # idx5 minimo central (fractal down)
        _c(3800, band + 0.00010, band + 0.00050, band + 0.00030, band + 0.00040),  # idx6
        _c(4100, band + 0.00040, band + 0.00070, band + 0.00035, band + 0.00060),  # idx7
    ]
    ev = evaluate_strat_f(_flat_15m(), m5, _m1_reject_low(), payout=85, zone_min_age=3)
    assert ev.has_signal is False
    assert "joven" in (ev.skip_reason or "")


def test_r6_score_bajo_rechaza():
    """R6 — strength*100 < min_score -> rechazo aunque haya señal válida."""
    ev = evaluate_strat_f(_flat_15m(), _fractal_down_5m(), _m1_reject_low(), payout=85, min_score=999)
    assert ev.has_signal is False
    assert "score" in (ev.skip_reason or "")


def test_r1_alineacion_m15_m5_downtrend_call():
    """R1 — CALL (fractal down) contra downtrend M15 -> rechazo."""
    ev = evaluate_strat_f(_downtrend_15m(), _fractal_down_5m(), _m1_reject_low(), payout=85)
    assert ev.has_signal is False
    assert "contra tendencia" in (ev.skip_reason or "")
