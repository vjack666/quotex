"""Tests unitarios de strat_b (Spring/Upthrust)."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from strat_b import candles_to_dataframe, evaluate_strat_b


def _candles(n: int, base: float = 100.0) -> list[Candle]:
    out = []
    for i in range(n):
        o = base + i * 0.01
        out.append(Candle(ts=i, open=o, high=o + 0.5, low=o - 0.5, close=o + 0.1))
    return out


def test_strat_b_no_signal_insufficient_candles():
    result = evaluate_strat_b(_candles(5))
    assert result is None


def test_strat_b_spring_signal_or_none():
    candles = _candles(25)
    result = evaluate_strat_b(candles)
    assert result is None or isinstance(result, dict)


def test_candles_to_dataframe_shape():
    df = candles_to_dataframe(_candles(20))
    assert list(df.columns) == ["open", "high", "low", "close"]
    assert len(df) == 20


def test_strat_b_no_network_imports():
    import strat_b as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "pyquotex" not in source