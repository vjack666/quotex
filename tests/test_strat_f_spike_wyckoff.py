"""Tests del spec strat_f_spike_wyckoff_phase_a (Fase A Wyckoff + separacion).

Cubre los puntos del spec que NO estaban en el test SPIKE base:
  (a) REBOTE base valido sigue intacto (entry_mode REBOUND, spike=False).
  (b) CALL spring confirmado -> SPIKE + wyckoff_event=spring + exhaustion_candle.
  (c) PUT upthrust confirmado -> SPIKE + wyckoff_event=upthrust.
  (d) Camino atrapado (R4-bis): stoch atrapado en extremo SIN vela de rechazo -> SPIKE.
  (e) INTRAVELA (R10): el agotamiento se detecta sobre la M15 ABIERTA via M1
      (lookback=15). evaluate_strat_f DEBE pasar candles_1m al motor.
  (f) M5 EN CONTRA (R3 filtro de paciencia): NO SPIKE (queda REBOUND).
  (g) R2-bis SEPARACION ADAPTATIVA: cruce-pegajoso (lineas pegadas, sep_rel bajo)
      -> el motor devuelve EXHAUST_WAIT y NO promueve a SPIKE. La separacion se
      mide RELATIVA al rango reciente de |K-D|, nunca en puntos fijos.
  (h) R3/R3-bis SEPARADOS: M5 ALINEADO (no en contra) PERO NO AGOTADO -> NO SPIKE;
      M5 AGOTADO PERO NO ALINEADO (en contra) -> NO SPIKE. Solo ALINEADO+AGOTADO
      (ambos a la vez) promueve.

Se mockea apply_stoch_help (el motor real esta en test_stochastic_zones /
test_stoch_exhaustion) y se verifican los campos nuevos separation_ok/rel.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from strat_fractal import evaluate_strat_f
from stochastic_zones import StochHelpResult
from stoch_exhaustion import ExhaustResult, evaluate_exhaustion


def _candle(o, h, l, c, ts):
    return SimpleNamespace(ts=float(ts), open=o, high=h, low=l, close=c,
                           ticks=5, body=abs(c - o))


def _range_15m():
    # M15 plano -> ctx "range" (CALL no es contra-tendencia)
    return [_candle(100, 101, 99, 100, i) for i in range(15)]


def _m5_with_fractal_down(band: float):
    m5 = [_candle(100, 101, 99, 100, i) for i in range(5)]
    m5.append(_candle(band + 1, band + 1.5, band, band + 0.8, 5))
    for j in range(4):
        base = band + 0.8 + j * 0.4
        m5.append(_candle(base - 0.2, base + 0.3, base - 0.3, base, 6 + j))
    return m5


def _m5_with_fractal_up(band: float):
    m5 = [_candle(100, 101, 99, 100, i) for i in range(5)]
    m5.append(_candle(band - 1.5, band, band - 1.2, band - 1.0, 5))
    for j in range(4):
        base = band - 1.0 - j * 0.4
        m5.append(_candle(base + 0.2, base + 0.3, base - 0.3, base, 6 + j))
    return m5


def _m1_rejecting_band(band: float):
    tol = band * 0.0015
    prev = _candle(band, band + 0.3, band, band + 0.05, 100)
    last = _candle(band, band + 0.4, band, band + 0.1 + tol, 101)
    return [prev, last]


def _m1_rejecting_band_up(band: float):
    tol = band * 0.0015
    prev = _candle(band, band, band - 0.3, band - 0.05, 100)
    last = _candle(band, band, band - 0.4, band - 0.1 - tol, 101)
    return [prev, last]


def _boost_exhaust(path: str, candle: str, *, sep_ok=None, sep_rel=None):
    ex = ExhaustResult(
        "EXHAUST_CONFIRMED", "agotamiento_confirmado",
        in_extreme_zone=True, cross_confirmed=True, cross_ago=2,
        exhaustion_candle=candle, path=path,
        separation_ok=sep_ok, separation_rel=sep_rel,
    )
    return StochHelpResult(zone="Z1", action="BOOST", score_delta=12,
                           reason="stoch_exhaust_confirmed", exhaustion=ex)


def _wait_exhaust(reason: str, *, sep_ok=None, sep_rel=None):
    ex = ExhaustResult(
        "EXHAUST_WAIT", reason,
        in_extreme_zone=True, cross_confirmed=True, cross_ago=2,
        separation_ok=sep_ok, separation_rel=sep_rel,
    )
    return StochHelpResult(zone="Z1", action="PASS", score_delta=0,
                           reason=f"stoch_exhaust_wait:{reason}", exhaustion=ex)


# ── (a) REBOTE base sin agotamiento: NO SPIKE ──

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


# ── (b) CALL spring confirmado -> SPIKE + wyckoff_event=spring ──

def test_spike_call_spring_confirmado():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_boost_exhaust("ruptura", "martillo", sep_ok=True, sep_rel=0.62)):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is True
    assert ev.entry_mode == "SPIKE"
    assert ev.wyckoff_event == "spring"
    assert ev.exhaustion_candle == "martillo"
    assert ev.separation_ok is True
    assert ev.separation_rel == 0.62


# ── (c) PUT upthrust confirmado -> SPIKE + wyckoff_event=upthrust ──

def test_spike_put_upthrust_confirmado():
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_boost_exhaust("ruptura", "estrellafugaz", sep_ok=True, sep_rel=0.55)):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is True
    assert ev.wyckoff_event == "upthrust"
    assert ev.exhaustion_candle == "estrellafugaz"
    assert ev.separation_ok is True


# ── (d) CAMINO ATRAPADO (R4-bis) ──

def test_spike_camino_atrapado_sin_vela_rechazo():
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_boost_exhaust("atrapado", "atrapado", sep_ok=True, sep_rel=0.70)):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is True
    assert ev.entry_mode == "SPIKE"
    assert ev.separation_ok is True


# ── (e) INTRAVELA (R10) ──

def test_spike_intravela_usa_candles_1m():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    captured = {}

    def _fake_help(k, direction, mode, **kw):
        captured.update(kw)
        if kw.get("candles_1m"):
            return _boost_exhaust("ruptura", "martillo", sep_ok=True, sep_rel=0.5)
        return StochHelpResult(zone="Z1", action="PASS", score_delta=0,
                               reason="stoch_exhaust_wait:sin_vela")

    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help", side_effect=_fake_help):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert captured.get("candles_1m") is not None, "evaluate_strat_f no paso candles_1m"
    assert captured.get("lookback") == 15, "lookback intravela debe ser 15"
    assert ev.spike is True, "INTRAVELA: senal debio detectarse antes de cerrar M15"


# ── (f) M5 EN CONTRA (R3) ──

def test_spike_m5_contra_bloquea():
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help", return_value=StochHelpResult(
             zone="Z5", action="PASS", score_delta=0, reason="stoch_exhaust_wait:m5_contra")):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is False, "M5 en contra -> filtro de paciencia, NO SPIKE"
    assert ev.entry_mode == "REBOUND"


# ── (g) R2-bis SEPARACION ADAPTATIVA: cruce pegajoso NO promueve ──

def test_spike_separacion_pegajosa_bloquea():
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    # Motor: cruce confirmado PERO lineas pegadas (sep_rel bajo) -> EXHAUST_WAIT
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_wait_exhaust("cruce_pegajoso:sep_rel=0.12", sep_ok=False, sep_rel=0.12)):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is False, "R2-bis: separacion pegajosa no debe promover SPIKE"
    assert ev.separation_ok is False
    # La medida es RELATIVA (0.12 = 12% del rango reciente), nunca puntos fijos
    assert ev.separation_rel == 0.12


def test_cross_separation_adaptativa_relativa():
    """Unidad de _cross_separation: misma separacion ABSOLUTA da veredicto
    distinto segun el rango reciente del par (doctrina: relativa, no fija)."""
    from stoch_exhaustion import _cross_separation
    # Par A: rango |K-D| grande (10) -> |K-D| actual 4 => rel 0.4 >= 0.35 OK
    ok_a, rel_a = _cross_separation([10.0, 8.0, 6.0, 4.0], [0.0, 0.0, 0.0, 0.0])
    # Par B: rango |K-D| pequeno (2) -> |K-D| actual 4 imposible, simulamos
    # serie donde el maximo reciente es 12 => actual 4 => rel 0.33 < 0.35 espera
    ok_b, rel_b = _cross_separation([12.0, 9.0, 7.0, 4.0], [0.0, 0.0, 0.0, 0.0])
    assert ok_a is True and rel_a == 0.4
    assert ok_b is False and rel_b == 0.3333
    # Ninguno usa umbral absoluto "3-5 puntos": ambos dependen del rango propio
    assert rel_a != rel_b or ok_a != ok_b  # la vara es el comportamiento del par


# ── (h) R3/R3-bis SEPARADOS: alineado sin agotar, y agotado sin alinear ──

def test_spike_m5_alineado_pero_no_agotado_bloquea():
    """R3 cumple (M5 alineado) PERO R3-bis no (M5 no agotado) -> NO SPIKE.
    El motor refleja esto como EXHAUST_WAIT 'm5_no_exhausted' (razon distinta
    a 'm5_contra' de R3), para que la caja negra las diferencie."""
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_wait_exhaust("m5_no_exhausted", sep_ok=True, sep_rel=0.5)):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is False, "R3-bis: M5 no agotado -> NO SPIKE aunque R3 alineado"


def test_spike_m5_agotado_pero_contra_bloquea():
    """R3-bis cumple (M5 agotado) PERO R3 no (M5 en contra) -> NO SPIKE.
    El motor devuelve EXHAUST_WAIT 'm5_contra' (R3), razon distinta a R3-bis."""
    band = 103
    m5 = _m5_with_fractal_up(band)
    m1 = _m1_rejecting_band_up(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_wait_exhaust("m5_contra", sep_ok=True, sep_rel=0.5)):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal
    assert ev.spike is False, "R3: M5 en contra -> NO SPIKE aunque R3-bis agotado"
    assert ev.entry_mode == "REBOUND"


# ── R3-bis a nivel de evaluate_exhaustion (autonomo del spec) ──

def test_r3bis_m5_no_exhausted_bloquea():
    """R3-bis: M5 alineado PERO no agotado -> EXHAUST_WAIT m5_no_exhausted.
    Razon distinta a m5_contra (R3). Cubre el punto exacto del spec: M5
    agotado en su extremo es condicion SEPARADA de la alineacion.

    Para llegar al chequeo R3-bis, el M15 debe tener cruce confirmado:
    K y D cruzan alcista (K sube cruzando D hacia arriba) en sobreventa CALL.
    """
    # K cruza alcista dentro de sobreventa CALL (k<=20): k0<=d0 y k1>d1 en
    # algun punto, y la separacion final |K-D| es >=35% del max reciente.
    # k final=18 (<=20 -> in_extreme CALL). d baja a 9 -> |18-9|=9, y el
    # max reciente de |K-D| es 22 (idx0) -> rel=0.409 >= 0.35 (pasa R2-bis).
    k_vals = [8.0, 10.0, 12.0, 18.0, 19.0, 18.0]
    d_vals = [30.0, 28.0, 22.0, 16.0, 11.0, 9.0]  # K cruza D en idx 3 (12<=22 -> 18>16)
    stoch_m5 = {"k": 55.0, "d": 50.0, "cruce": "alcista"}  # alineado, NO agotado (<20)
    ex = evaluate_exhaustion(
        k=18.0, d=9.0, k_vals=k_vals, d_vals=d_vals, direction="CALL",
        candles_15m=None, stoch_m5=stoch_m5, zone_lo=95.0, zone_hi=97.0,
    )
    assert ex.action == "EXHAUST_WAIT"
    assert ex.reason == "m5_no_exhausted"
    assert ex.separation_ok is True  # separacion no es el bloqueo aqui


def test_r3bis_m5_exhausted_pasa():
    """R3-bis + R3 cumplen (M5 agotado k=12 CALL y alineado) -> sigue adelante
    hacia el camino de confirmacion (no se corta en m5_no_exhausted)."""
    k_vals = [8.0, 10.0, 12.0, 18.0, 19.0, 18.0]
    d_vals = [30.0, 28.0, 22.0, 16.0, 11.0, 9.0]
    stoch_m5 = {"k": 12.0, "d": 18.0, "cruce": "alcista"}  # agotado + a favor
    ex = evaluate_exhaustion(
        k=18.0, d=9.0, k_vals=k_vals, d_vals=d_vals, direction="CALL",
        candles_15m=None, stoch_m5=stoch_m5, zone_lo=95.0, zone_hi=97.0,
    )
    # No se corta en m5_contra ni m5_no_exhausted; llega al chequeo de vela/atrapado
    assert ex.reason not in ("m5_contra", "m5_no_exhausted")


# ── MODO OBSERVACIÓN (Ruben 2026-07-26): SPIKE registra breakdown y NO opera ──

def test_modo_observacion_spike_no_opera():
    """Con STRAT_F_SPIKE_OBSERVE=True, un setup SPIKE candidato debe devolver
    has_signal=False y decision='OBSERVE', con el desglose de las 6 condiciones
    en spike_observe, PERO sin operar. Verifica que el modo observacion
    registra sin enviar orden."""
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_boost_exhaust("ruptura", "martillo", sep_ok=True, sep_rel=0.6)), \
         patch("strat_fractal.STRAT_F_SPIKE_OBSERVE", True):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal is False, "modo observacion: NO debe operar"
    assert ev.decision == "OBSERVE"
    assert ev.spike is True  # el setup SI es SPIKE, solo que no opera
    assert isinstance(ev.spike_observe, dict)
    # breakdown de las 6 condiciones presentes (la que falta por datos queda None)
    assert "R2_zona_franja" in ev.spike_observe
    assert "R2bis_separacion_abierta" in ev.spike_observe
    assert "cruce_m15_confirmado" in ev.spike_observe
    assert "R3_m5_alineado" in ev.spike_observe
    assert "R3bis_m5_agotado" in ev.spike_observe
    assert "R4_rechazo_o_atrapado" in ev.spike_observe


def test_modo_observacion_off_opera_normal():
    """Con STRAT_F_SPIKE_OBSERVE=False (default), el SPIKE opera normalmente
    (has_signal=True, decision=None). El observador no debe silenciar nada."""
    band = 96.5
    m5 = _m5_with_fractal_down(band)
    m1 = _m1_rejecting_band(band)
    with patch("strat_fractal.compute_stoch", return_value={"k": 50.0, "d": 50.0}), \
         patch("strat_fractal.apply_stoch_help",
               return_value=_boost_exhaust("ruptura", "martillo", sep_ok=True, sep_rel=0.6)), \
         patch("strat_fractal.STRAT_F_SPIKE_OBSERVE", False):
        ev = evaluate_strat_f(_range_15m(), m5, m1, payout=90)
    assert ev.has_signal is True, "modo normal: el SPIKE debe operar"
    assert ev.decision is None
    assert ev.spike is True
