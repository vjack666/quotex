"""Modo SPIKE de STRAT-F (V3): agotamiento verdadero + Fase A Wyckoff.

Reescribe el test viejo (cuerpo-a-favor) para la nueva semantica: el SPIKE
ahora se activa cuando apply_stoch_help devuelve BOOST por agotamiento
confirmado (cruce M15 + M5 alineado + vela de rechazo en la zona S/R,
o stoch atrapado en extremo). Mapea a spring (CALL) / upthrust (PUT).

Se mockea apply_stoch_help para aislar la propagacion del SPIKE dentro de
evaluate_strat_f (el motor real esta cubierto en test_stochastic_zones y
test_stoch_exhaustion). El caso (e) INTRAVELA verifica que evaluate_strat_f
le pasa candles_1m a apply_stoch_help (R10).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from strat_fractal import evaluate_strat_f
from stochastic_zones import StochHelpResult
from stoch_exhaustion import ExhaustResult


def _candle(o, h, l, c, ts):
    return SimpleNamespace(ts=float(ts), open=o, high=h, low=l, close=c,
                           ticks=5, body=abs(c - o))


def _range_15m():
    # M15 plano -> ctx "range" (CALL no es contra-tendencia)
    return [_candle(100, 101, 99, 100, i) for i in range(15)]


def _m5_with_fractal_down(band: float):
    """M5 con fractal_down real (Bill Williams). Infiere direccion CALL.
    Velas planas ~100; idx5 hunde el low al nivel `band`."""
    m5 = [_candle(100, 101, 99, 100, i) for i in range(5)]
    m5.append(_candle(band + 1, band + 1.5, band, band + 0.8, 5))  # low hundido = band
    for j in range(4):  # rebote suave post-fractal
        base = band + 0.8 + j * 0.4
        m5.append(_candle(base - 0.2, base + 0.3, base - 0.3, base, 6 + j))
    return m5


def _m5_with_fractal_up(band: float):
    """M5 con fractal_up real (Bill Williams). Infiere direccion PUT.
    Velas planas ~100 (high=101); idx5 clava el high en `band` (techo > 101)."""
    m5 = [_candle(100, 101, 99, 100, i) for i in range(5)]
    m5.append(_candle(band - 1.5, band, band - 1.2, band - 1.0, 5))  # high clavado = band
    for j in range(4):  # rebote suave post-fractal (baja del techo)
        base = band - 1.0 - j * 0.4
        m5.append(_candle(base + 0.2, base + 0.3, base - 0.3, base, 6 + j))
    return m5


def _m1_rejecting_band(band: float):
    """Dos velas M1 que rechazan la banda S/R (CALL: low toca band, cierra arriba)."""
    tol = band * 0.0015
    prev = _candle(band, band + 0.3, band, band + 0.05, 100)
    last = _candle(band, band + 0.4, band, band + 0.1 + tol, 101)
    return [prev, last]


def _m1_rejecting_band_up(band: float):
    """Dos velas M1 que rechazan el techo S/R (PUT: high toca band, cierra abajo)."""
    tol = band * 0.0015
    prev = _candle(band, band, band - 0.3, band - 0.05, 100)
    last = _candle(band, band, band - 0.4, band - 0.1 - tol, 101)
    return [prev, last]


def _boost_exhaust(path: str, candle: str):
    ex = ExhaustResult(
        "EXHAUST_CONFIRMED", "agotamiento_confirmado",
        in_extreme_zone=True, cross_confirmed=True, cross_ago=2,
        exhaustion_candle=candle, path=path,
    )
    return StochHelpResult(zone="Z1", action="BOOST", score_delta=12,
                           reason="stoch_exhaust_confirmed", exhaustion=ex)


# ── (a) REBOTE base sin agotamiento: NO SPIKE ──────────────────────

def test_rebote_base_valido():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help", return_value=StochHelpResult(
             zone="Z1", action="PASS", score_delta=0, reason="stoch_exhaust_wait:x")):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal, f"se esperaba senal REBOTE, skip={ev.skip_reason}"
    assert ev.entry_mode == "REBOUND"
    assert ev.spike is False


# ── (b) CALL spring confirmado -> SPIKE + wyckoff_event=spring ──────

def test_spike_call_spring_confirmado():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help", return_value=_boost_exhaust("ruptura", "martillo")):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is True
    assert ev.entry_mode == "SPIKE"
    assert ev.wyckoff_event == "spring"
    assert ev.exhaustion_candle == "martillo"


# ── (c) PUT upthrust confirmado -> SPIKE + wyckoff_event=upthrust ──

def test_spike_put_upthrust_confirmado():
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
                return_value=_boost_exhaust("ruptura", "estrellafugaz")):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is True
    assert ev.wyckoff_event == "upthrust"
    assert ev.exhaustion_candle == "estrellafugaz"


# ── (d) CAMINO ATRAPADO (R4-bis): sin vela rechazo, stoch atrapado ──

def test_spike_camino_atrapado_sin_vela_rechazo():
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
                return_value=_boost_exhaust("atrapado", "atrapado")):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is True
    assert ev.entry_mode == "SPIKE"


# ── (e) INTRAVELA (R10): el agotamiento se detecta en candles_1m ─────
#     (la M15 aun no cierra). evaluate_strat_f DEBE pasar candles_1m a
#     apply_stoch_help para que el motor lo vea.

def test_spike_intravela_usa_candles_1m():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)

    captured = {}

    def _fake_help(k, direction, mode, **kw):
        captured.update(kw)
        # Solo confirma si recibio candles_1m (el agotamiento vive en M1)
        if kw.get("candles_1m"):
            return _boost_exhaust("ruptura", "martillo")
        return StochHelpResult(zone="Z1", action="PASS", score_delta=0,
                               reason="stoch_exhaust_wait:sin_vela")

    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help", side_effect=_fake_help):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    # El SPIKE solo se activa si evaluate_strat_f cableo candles_1m (R10)
    assert captured.get("candles_1m") is not None, "evaluate_strat_f no paso candles_1m"
    assert captured.get("lookback") == 15, "lookback intravela debe ser 15"
    assert ev.spike is True, "INTRAVELA: senal debio detectarse antes de cerrar M15"


# ── (f) M5 EN CONTRA (filtro de paciencia, R3): NO SPIKE ──────────

def test_spike_m5_contra_bloquea():
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    # apply_stoch_help devuelve PASS (m5_contra) -> NO promueve a SPIKE
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help", return_value=StochHelpResult(
             zone="Z5", action="PASS", score_delta=0, reason="stoch_exhaust_wait:m5_contra")):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is False, "M5 en contra -> filtro de paciencia, NO SPIKE"
    assert ev.entry_mode == "REBOUND"
