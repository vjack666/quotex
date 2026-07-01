"""Tests unitarios de strat_a (lógica pura)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from strat_a import (
    broke_above,
    broke_below,
    detect_consolidation,
    price_at_ceiling,
    validate_rejection_candle,
)


def _flat_candle(ts: int, price: float, body: float = 0.0001) -> Candle:
    return Candle(ts=ts, open=price, high=price + body, low=price - body, close=price + body)


def _make_tight_consolidation(n: int = 15, base: float = 1.1000) -> list[Candle]:
    candles = []
    for i in range(n):
        p = base + (0.0001 if i % 2 == 0 else -0.0001)
        candles.append(_flat_candle(1000 + i * 300, p, 0.00005))
    return candles


def test_detect_consolidation_valid_zone():
    candles = _make_tight_consolidation()
    zone = detect_consolidation(candles, max_range_pct=0.01)
    assert zone is not None
    assert zone.ceiling >= zone.floor
    assert zone.bars_inside >= 12


def test_broke_above_detects_breakout():
    ceiling = 1.1050
    candle = Candle(ts=1, open=1.1040, high=1.1060, low=1.1030, close=1.1060)
    assert broke_above(candle, ceiling) is True


def test_price_at_ceiling_within_tolerance():
    assert price_at_ceiling(1.1000, 1.1000, tolerance_pct=0.001) is True


def test_validate_rejection_candle_call_ok():
    candles = [
        Candle(ts=1, open=1.0, high=1.01, low=0.99, close=1.0),
        Candle(ts=2, open=1.0, high=1.02, low=0.99, close=1.015),
        Candle(ts=3, open=1.01, high=1.02, low=1.0, close=1.018),
    ]
    ok, reason = validate_rejection_candle(candles, "call")
    assert ok is True
    assert reason == ""


def test_strat_a_no_side_effects(monkeypatch):
    """R12: sin I/O de red ni archivos."""
    called = {"network": False}

    def fake_import(name, *args, **kwargs):
        if name == "pyquotex" or name.startswith("pyquotex."):
            called["network"] = True
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)
    zone = detect_consolidation(_make_tight_consolidation())
    assert zone is not None
    assert called["network"] is False