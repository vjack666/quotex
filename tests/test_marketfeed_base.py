"""T1 — Event y contrato base (R1.1, R2.1)."""
import dataclasses

import pytest

from marketfeed.base import (
    Event,
    KIND_CANDLE_CLOSED,
    KIND_FEED_GAP,
    KIND_TICK,
    VALID_KINDS,
)


def test_event_valido_se_construye():
    e = Event(kind=KIND_CANDLE_CLOSED, asset="EURUSD", ts=1000.0,
              payload={"close": 1.1}, source="LIVE:quotex")
    assert e.kind == KIND_CANDLE_CLOSED
    assert e.asset == "EURUSD"
    assert e.ts == 1000.0
    assert e.payload["close"] == 1.1
    assert e.source == "LIVE:quotex"


def test_event_es_inmutable_frozen():
    e = Event(kind=KIND_TICK, asset="EURUSD", ts=1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.ts = 2.0


def test_kind_invalido_valueerror():
    with pytest.raises(ValueError):
        Event(kind="PRESION", asset="EURUSD", ts=1.0)


def test_asset_vacio_valueerror():
    with pytest.raises(ValueError):
        Event(kind=KIND_TICK, asset="", ts=1.0)


def test_ts_no_numerico_valueerror():
    with pytest.raises(ValueError):
        Event(kind=KIND_TICK, asset="EURUSD", ts="ayer")


def test_valid_kinds_exactos():
    assert VALID_KINDS == {KIND_CANDLE_CLOSED, KIND_TICK, KIND_FEED_GAP}
