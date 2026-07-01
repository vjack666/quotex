"""Tests de strat_momentum.py."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from strat_momentum import detect_momentum_1m


def _base_candles(count: int = 11, body: float = 0.001) -> list[Candle]:
    candles: list[Candle] = []
    for i in range(count):
        o = 1.0
        c = o + body
        candles.append(
            Candle(
                ts=i * 60,
                open=o,
                high=max(o, c) + 0.0002,
                low=min(o, c) - 0.0002,
                close=c,
            )
        )
    return candles


def test_momentum_detect_bullish():
    candles = _base_candles()
    last = candles[-1]
    candles[-1] = Candle(
        ts=last.ts,
        open=1.0,
        high=1.010,
        low=1.0,
        close=1.009,
    )

    result = detect_momentum_1m(candles)

    assert result is not None
    direction, strength = result
    assert direction == "call"
    assert 0.0 < strength <= 1.0


def test_momentum_detect_bearish():
    candles = _base_candles()
    last = candles[-1]
    candles[-1] = Candle(
        ts=last.ts,
        open=1.010,
        high=1.010,
        low=1.0,
        close=1.001,
    )

    result = detect_momentum_1m(candles)

    assert result is not None
    direction, strength = result
    assert direction == "put"
    assert 0.0 < strength <= 1.0


def test_momentum_detect_no_signal_small_body():
    candles = _base_candles()
    last = candles[-1]
    candles[-1] = Candle(
        ts=last.ts,
        open=1.0,
        high=1.010,
        low=1.0,
        close=1.0005,
    )

    assert detect_momentum_1m(candles) is None


def test_momentum_detect_no_signal_wrong_close_zone():
    candles = _base_candles()
    last = candles[-1]
    candles[-1] = Candle(
        ts=last.ts,
        open=1.0,
        high=1.010,
        low=1.0,
        close=1.005,
    )

    assert detect_momentum_1m(candles) is None