"""Tests de regresión para sequence_engine.py (comportamiento vigente)."""
from __future__ import annotations

import pytest

from sequence_engine import SequenceCard, SequenceEngine, FLOOR_INDEX


def test_reception_rejects_low_payout() -> None:
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    transition = engine.evaluate(card, {"payout": 70, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    assert transition.allowed is False
    assert transition.reject_reason == "RECHAZAR_RECEPCION"
    assert card.current_floor == "RECEPCION"


def test_reception_rejects_brake_false() -> None:
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    transition = engine.evaluate(card, {"payout": 90, "brake_ok": False, "extreme_ok": True}, timestamp="t1")
    assert transition.allowed is False
    assert card.current_floor == "RECEPCION"


def test_cerebro_rejects_insufficient_kd() -> None:
    engine = SequenceEngine(min_dwell_ticks={"RECEPCION": 1, "CANDIDATO": 1, "CEREBRO": 1, "ENTRADA": 0})
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    card.tick()
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t2")
    card.tick()
    transition = engine.evaluate(card, {"cross_ok": True, "cross_limpieza_ok": True, "kd_distance": 1.5}, timestamp="t3")
    assert transition.allowed is False
    assert transition.reject_reason == "RECHAZAR_CEREBRO"
    assert card.current_floor == "CEREBRO"


def test_valid_pipeline_reaches_entrada() -> None:
    engine = SequenceEngine(min_dwell_ticks={"RECEPCION": 1, "CANDIDATO": 1, "CEREBRO": 1, "ENTRADA": 0})
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t1")
    assert card.current_floor == "CANDIDATO"
    card.tick()
    engine.evaluate(card, {"payout": 90, "brake_ok": True, "extreme_ok": True}, timestamp="t2")
    assert card.current_floor == "CEREBRO"
    card.tick()
    engine.evaluate(card, {"cross_ok": True, "cross_limpieza_ok": True, "kd_distance": 2.0}, timestamp="t3")
    assert card.current_floor == "ENTRADA"


def test_cannot_skip_floor() -> None:
    engine = SequenceEngine()
    card = SequenceCard(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    card.current_floor = "CEREBRO"
    transition = engine.evaluate(card, {"cross_ok": True, "cross_limpieza_ok": True, "kd_distance": 2.0}, timestamp="t1")
    assert transition.from_floor == "CEREBRO"
    assert transition.to_floor == "CEREBRO"
