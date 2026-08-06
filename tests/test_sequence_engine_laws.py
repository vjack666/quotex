"""Tests de conformidad del SequenceEngine con el documento maestro de 12 leyes.

No usa terminología de ninguna teoría de trading: solo valida la mecánica de
secuencias (vela a vela, candidato->confirmado, grafo de dependencias,
invalidación predefinida, trazabilidad).
"""
from __future__ import annotations

import pytest

from sequence_engine import SequenceCard, SequenceEngine, FLOOR_INDEX


# ── Ley 1: causalidad vela a vela / sin tiempo de pared ──────────────────────
def test_evaluate_requires_explicit_timestamp() -> None:
    """Ley 1: el motor no debe inventar el instante con datetime.utcnow().
    Quien llama debe pasar el sello de la vela que se procesa."""
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    with pytest.raises(ValueError):
        engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp=None)


def test_timestamp_is_recorded_on_transition() -> None:
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    ts = "2026-08-05T12:00:00Z"
    t = engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp=ts)
    assert t.timestamp == ts


# ── Ley 4: candidato vs confirmado ───────────────────────────────────────────
def test_reception_has_candidate_then_confirmed() -> None:
    """Ley 4: RECEPCION pasa primero por CANDIDATO (pendiente de confirmación)
    antes de avanzar a CEREBRO. El candidato no es el evento confirmado."""
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    assert card.current_floor == "CANDIDATO"
    # segunda vela: el candidato se confirma y avanza a CEREBRO
    card.tick()
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t2")
    assert card.current_floor == "CEREBRO"


def test_reception_candidate_rejected_is_not_confirmed() -> None:
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    t = engine.evaluate(card, {"payout": 70, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    assert t.allowed is False
    assert card.current_floor == "RECEPCION"  # sigue en piso origen, no CANDIDATO


# ── Ley 5/3: jerarquía / grafo de dependencias ───────────────────────────────
def test_cannot_advance_without_dependency_active() -> None:
    """Ley 5: CEREBRO no puede nacer si RECEPCION no está confirmada.
    Forzar el piso por fuera no debe producir un avance real."""
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    card.current_floor = "CEREBRO"  # alguien lo forzó por fuera
    t = engine.evaluate(card, {"cross_ok": True, "cross_limpieza_ok": True, "kd_distance": 2.0}, timestamp="t1")
    # el motor detecta que la dependencia (RECEPCION confirmada) no está y lo devuelve
    assert t.allowed is False
    assert t.reject_reason == "DEPENDENCIA_INACTIVA"


# ── Ley 6/8: invalidación predefinida + trazabilidad ─────────────────────────
def test_transition_records_invalidation_condition() -> None:
    """Ley 8: cada transición guarda la condición de invalidación declarada."""
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    t = engine.evaluate(card, {"payout": 70, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    assert t.invalidation_condition is not None
    assert isinstance(t.invalidation_condition, str) and t.invalidation_condition


def test_trace_logger_is_append_only() -> None:
    """Ley 8: los nacimientos/persistencias se registran en traza persistente."""
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    card.tick()
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t2")
    trace = engine.get_trace(card.hypothesis_id)
    assert len(trace) >= 2
    assert all(hasattr(e, "timestamp") and e.timestamp for e in trace)


# ── Ley 2/12: una evaluación por vela (sin while empujando) ──────────────────
def test_evaluate_does_not_loop_to_entrada() -> None:
    """Ley 2/12: una sola llamada a evaluate debe procesar SOLO la vela actual,
    no avanzar en bucle hasta ENTRADA. El llamador debe iterar vela a vela."""
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    t = engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    # tras una sola vela: llegó a CANDIDATO, no a ENTRADA
    assert card.current_floor == "CANDIDATO"
    assert card.current_floor != "ENTRADA"


# ── API heredada sigue viva ──────────────────────────────────────────────────
def test_legacy_api_still_passes() -> None:
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    card.tick()
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t2")
    card.tick()
    engine.evaluate(card, {"cross_ok": True, "cross_limpieza_ok": True, "kd_distance": 2.0}, timestamp="t3")
    # con los ticks de dwell correctos llega a ENTRADA
    assert card.current_floor == "ENTRADA"
    assert engine.is_contratado_valido(card)


# ── Unificación con strategy_lab/hypothesis.py ───────────────────────────────
def test_unified_discipline_with_strategy_lab() -> None:
    """Ley 5: ambas máquinas de pisos (el SequenceCard del Edificio y la
    Hypothesis del lab) comparten el mismo contrato de avance secuencial:
    no se salta un piso, el retroceso es explícito y la invalidación queda
    registrada (no se olvida en silencio)."""
    from strategy_lab.hypothesis import Floor, Hypothesis

    # Máquina del lab: avance +1 estricto.
    h = Hypothesis(hypothesis_id="L1", asset="EURUSD", direction="CALL")
    h.advance(Floor.CANDIDATO)  # OBSERVANDO -> CANDIDATO
    assert h.current_floor == Floor.CANDIDATO
    try:
        h.advance(Floor.EN_CRUCE)  # brincar +3 (debería fallar)
        assert False, "el lab debe rechazar avance no adyacente"
    except ValueError:
        pass

    # Máquina del Edificio: mismo contrato vía SequenceCard.
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="E1", asset="EURUSD", direction="CALL")
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    assert card.current_floor == "CANDIDATO"  # RECEPCION -> CANDIDATO (adyacente)
    # retroceso explícito a un piso confirmado
    card.retrocede("RECEPCION")
    assert card.current_floor == "RECEPCION"
    # retroceso a un piso no confirmado -> ilegal
    try:
        card.retrocede("ENTRADA")
        assert False, "SequenceCard debe rechazar retroceso a piso no confirmado"
    except ValueError:
        pass
    # invalidación queda registrada
    card.invalidate(reason="prueba")
    assert card.invalidated is True
    assert card.history[-1].reject_reason == "INVALIDADA"
