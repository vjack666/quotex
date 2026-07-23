"""Modo SPIKE de STRAT-F: condición ADICIONAL al rebote (no lo reemplaza).

Cuando hay patron de agotamiento (stoch M5 exhaust) y la vela de entrada toca
el extremo del fractal con CUERPO a favor, evaluate_strat_f promueve la senal a
entry_mode="SPIKE" / spike=True. Si no hay agotamiento, queda en REBOTE.

Se mockea compute_stoch para aislar la logica SPIKE (el stoch real necesita
muchas velas de sesion; aqui solo importa el valor %K inyectado).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from strat_fractal import evaluate_strat_f, stoch_m5_exhausted


def _candle(o, h, l, c, ts):
    return SimpleNamespace(ts=float(ts), open=o, high=h, low=l, close=c,
                           ticks=5, body=abs(c - o))


def _range_15m():
    # M15 plano -> ctx "range" (CALL no es contra-tendencia)
    return [_candle(100, 101, 99, 100, i) for i in range(15)]


def _m5_with_fractal_down(band: float):
    """Velas M5 con fractal_down real en idx 5 (Bill Williams, vecinos altos).

    Devuelve m5 con el fractal en idx 5 y 4 velas de rebote posteriores.
    """
    m5 = [_candle(100, 101, 99, 100, i) for i in range(5)]  # planas previas
    m5.append(_candle(band + 1, band + 1.5, band, band + 0.8, 5))  # fractal_down (low hundido)
    for j in range(4):  # rebote suave post-fractal
        base = band + 0.8 + j * 0.4
        m5.append(_candle(base - 0.2, base + 0.3, base - 0.3, base, 6 + j))
    return m5


def _m1_rejecting_band(band: float):
    """Dos velas M1 que rechazan la banda (CALL: tocan low, cierran arriba)."""
    tol = band * 0.0015
    prev = _candle(band, band + 0.3, band, band + 0.05, 100)
    last = _candle(band, band + 0.4, band, band + 0.1 + tol, 101)
    return [prev, last]


def test_rebote_base_valido():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal, f"se esperaba senal REBOTE, skip={ev.skip_reason}"
    assert ev.entry_mode == "REBOUND"
    assert ev.spike is False


def test_spike_cuando_hay_agotamiento_y_cuerpo_a_favor():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    # M1: rechaza banda Y tiene cuerpo a favor DOMINANTE cerca del extremo (SPIKE)
    tol = band * 0.0015
    prev = _candle(band, band + 0.3, band, band + 0.05, 100)
    # last: open=band, close=band+0.12, high=band+0.16, low=band -> cuerpo dominante (>=50% rango)
    last = _candle(band, band + 0.16, band, band + 0.12, 101)  # close>open (cuerpo a favor)
    m1 = [prev, last]
    # Agotamiento: stoch M5 %K < 20 para CALL
    with patch("strat_fractal.compute_stoch", return_value={"k": 10.0, "d": 12.0}):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal, f"se esperaba senal, skip={ev.skip_reason}"
    assert ev.spike is True, f"con agotamiento+cuerpo_a_favor debe ser SPIKE, mode={ev.entry_mode}"
    assert ev.entry_mode == "SPIKE"


def test_spike_no_se_activa_sin_cuerpo_a_favor():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    # M1 con cuerpo EN CONTRA (rebote, close<open) -> no debe ser SPIKE
    tol = band * 0.0015
    prev = _candle(band, band + 0.3, band, band + 0.05, 100)
    last = _candle(band + 0.2, band + 0.5, band, band + 0.05, 101)  # close<open (en contra)
    m1 = [prev, last]
    with patch("strat_fractal.compute_stoch", return_value={"k": 10.0, "d": 12.0}):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal, f"se esperaba senal REBOTE, skip={ev.skip_reason}"
    assert ev.spike is False, "cuerpo en contra -> no SPIKE (es rebote)"


def test_stoch_m5_exhausted_contrato():
    assert stoch_m5_exhausted(10.0, "CALL") is True
    assert stoch_m5_exhausted(50.0, "CALL") is False
    assert stoch_m5_exhausted(90.0, "PUT") is True
    assert stoch_m5_exhausted(None, "CALL") is False
