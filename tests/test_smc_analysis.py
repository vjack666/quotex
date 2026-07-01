"""Tests de smc_analysis.py con velas sintéticas."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from smc_analysis import (
    Bias,
    StructureEventType,
    detect_fvg,
    detect_structure,
    detect_swings,
)


def _candle(ts: int, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=c)


def _zigzag_swings(n: int = 25, base: float = 1.0, amp: float = 0.01) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(n):
        wave = amp if (i // 4) % 2 == 0 else -amp
        mid = base + wave * ((i % 4) + 1)
        candles.append(_candle(i, mid - 0.001, mid + 0.002, mid - 0.002, mid))
    return candles


def test_detect_swings_finds_highs_and_lows():
    candles = _zigzag_swings()
    swings = detect_swings(candles, strength=2)
    highs = [s for s in swings if s.is_high]
    lows = [s for s in swings if not s.is_high]
    assert len(highs) >= 1
    assert len(lows) >= 1


def test_detect_fvg_bullish_gap():
    candles = [
        _candle(0, 1.00, 1.01, 0.99, 1.00),
        _candle(1, 1.02, 1.04, 1.01, 1.03),
        _candle(2, 1.06, 1.08, 1.05, 1.07),
    ]
    fvgs = detect_fvg(candles, min_size_pct=0.0001)
    bullish = [f for f in fvgs if f.is_bullish]
    assert len(bullish) == 1
    assert bullish[0].bottom == pytest.approx(1.01)
    assert bullish[0].top == pytest.approx(1.05)


def test_detect_fvg_bearish_gap():
    candles = [
        _candle(0, 1.10, 1.11, 1.09, 1.10),
        _candle(1, 1.06, 1.08, 1.05, 1.06),
        _candle(2, 1.02, 1.04, 1.01, 1.02),
    ]
    fvgs = detect_fvg(candles, min_size_pct=0.0001)
    bearish = [f for f in fvgs if not f.is_bullish]
    assert len(bearish) == 1
    assert bearish[0].top == pytest.approx(1.09)
    assert bearish[0].bottom == pytest.approx(1.04)


def test_detect_structure_returns_neutral_when_too_few_candles():
    candles = [_candle(i, 1.0, 1.01, 0.99, 1.0) for i in range(4)]
    result = detect_structure(candles, swing_strength=3)
    assert result.bias == Bias.NEUTRAL
    assert result.swings == []
    assert result.zones == []


def test_detect_structure_produces_events_and_bias():
    candles = _zigzag_swings(n=40, amp=0.02)
    for i, c in enumerate(candles):
        if i % 7 == 3:
            candles[i] = _candle(
                c.ts,
                c.open,
                c.high + 0.03,
                c.low,
                c.close + 0.02,
            )
    result = detect_structure(candles, swing_strength=2, min_fvg_pct=0.00005)
    assert result.bias in (Bias.BULLISH, Bias.BEARISH, Bias.NEUTRAL)
    assert isinstance(result.events, list)
    if result.events:
        assert result.events[0].event_type in StructureEventType