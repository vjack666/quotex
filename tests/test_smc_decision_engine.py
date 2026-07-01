"""Tests de smc_decision_engine.py con resultados de estructura controlados."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from smc_analysis import (
    Bias,
    StructureEvent,
    StructureEventType,
    StructureResult,
    Zone,
)
from smc_decision_engine import SMCDecisionEngine, Signal


def _flat_candles(n: int) -> list[Candle]:
    return [Candle(ts=i, open=1.0, high=1.01, low=0.99, close=1.0) for i in range(n)]


def _structure(
    bias: Bias,
    *,
    events: list[StructureEvent] | None = None,
    zones: list[Zone] | None = None,
) -> StructureResult:
    return StructureResult(
        bias=bias,
        events=events or [],
        zones=zones or [],
    )


def _demand_zone() -> Zone:
    return Zone(top=1.02, bottom=1.00, is_supply=False, origin_ts=10, fvg_adjacent=True, score=1.0)


def _supply_zone() -> Zone:
    return Zone(top=1.05, bottom=1.03, is_supply=True, origin_ts=20, fvg_adjacent=True, score=1.0)


def _bos_up() -> StructureEvent:
    return StructureEvent(
        index=5, ts=5, event_type=StructureEventType.BOS_UP, broken_level=1.01,
    )


def _bos_down() -> StructureEvent:
    return StructureEvent(
        index=5, ts=5, event_type=StructureEventType.BOS_DOWN, broken_level=0.99,
    )


@patch("smc_decision_engine.detect_structure")
def test_h4_neutral_returns_wait(mock_detect):
    mock_detect.side_effect = [
        _structure(Bias.NEUTRAL),
        _structure(Bias.BULLISH),
        _structure(Bias.BULLISH),
    ]
    engine = SMCDecisionEngine(_flat_candles(20), _flat_candles(20), _flat_candles(20))
    decision = engine.decide()
    assert decision.signal == Signal.WAIT
    assert decision.h4_bias == Bias.NEUTRAL
    assert "H4 sin tendencia clara" in decision.reason


@patch("smc_decision_engine.detect_structure")
def test_m15_conflict_returns_wait(mock_detect):
    mock_detect.side_effect = [
        _structure(Bias.BEARISH),
        _structure(Bias.BULLISH),
        _structure(Bias.BEARISH, events=[_bos_down()]),
    ]
    engine = SMCDecisionEngine(_flat_candles(20), _flat_candles(20), _flat_candles(20))
    decision = engine.decide()
    assert decision.signal == Signal.WAIT
    assert "ESPERANDO ALINEACIÓN CON H4" in decision.reason


@patch("smc_decision_engine.detect_structure")
def test_bearish_alignment_returns_sell(mock_detect):
    mock_detect.side_effect = [
        _structure(Bias.BEARISH),
        _structure(Bias.BEARISH, zones=[_supply_zone()]),
        _structure(Bias.BEARISH, events=[_bos_down()]),
    ]
    engine = SMCDecisionEngine(_flat_candles(20), _flat_candles(20), _flat_candles(20))
    decision = engine.decide()
    assert decision.signal == Signal.SELL
    assert decision.best_zone is not None
    assert decision.best_zone.is_supply is True


@patch("smc_decision_engine.detect_structure")
def test_bullish_alignment_returns_buy(mock_detect):
    mock_detect.side_effect = [
        _structure(Bias.BULLISH),
        _structure(Bias.BULLISH, zones=[_demand_zone()]),
        _structure(Bias.BULLISH, events=[_bos_up()]),
    ]
    engine = SMCDecisionEngine(_flat_candles(20), _flat_candles(20), _flat_candles(20))
    decision = engine.decide()
    assert decision.signal == Signal.BUY
    assert decision.best_zone is not None
    assert decision.best_zone.is_supply is False


@patch("smc_decision_engine.detect_structure")
def test_m1_choch_trap_returns_wait(mock_detect):
    trap = StructureEvent(
        index=6, ts=6, event_type=StructureEventType.CHOCH_UP, broken_level=1.02,
    )
    mock_detect.side_effect = [
        _structure(Bias.BEARISH),
        _structure(Bias.BEARISH, zones=[_supply_zone()]),
        _structure(Bias.BEARISH, events=[trap]),
    ]
    engine = SMCDecisionEngine(_flat_candles(20), _flat_candles(20), _flat_candles(20))
    decision = engine.decide()
    assert decision.signal == Signal.WAIT
    assert "trampa alcista" in decision.reason