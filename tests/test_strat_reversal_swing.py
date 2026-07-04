"""Tests de strat_reversal_swing.py."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from strat_reversal_swing import (
    SWING_LOOKBACK,
    detect_reversal_swing,
)


def _base_candles(
    count: int | None = None,
    swing_high_at: tuple[int, float] | None = None,
    swing_low_at: tuple[int, float] | None = None,
) -> list[Candle]:
    """Genera velas base con un swing opcional.

    Todas las velas base tienen precio ~1.0 con cuerpo pequeño y mechas de 0.002.
    """
    n = count or SWING_LOOKBACK + 1  # 13 velas por defecto
    candles: list[Candle] = []
    for i in range(n):
        if swing_high_at is not None and i == swing_high_at[0]:
            hl = swing_high_at[1]
            candles.append(
                Candle(
                    ts=i * 60,
                    open=hl - 0.02,
                    high=hl,
                    low=hl - 0.025,
                    close=hl - 0.01,
                )
            )
        elif swing_low_at is not None and i == swing_low_at[0]:
            ll = swing_low_at[1]
            candles.append(
                Candle(
                    ts=i * 60,
                    open=ll + 0.02,
                    high=ll + 0.025,
                    low=ll,
                    close=ll + 0.01,
                )
            )
        else:
            candles.append(
                Candle(
                    ts=i * 60,
                    open=1.0,
                    high=1.002,
                    low=0.998,
                    close=1.0,
                )
            )
    return candles


def _candles_with_swing_high(high_level: float = 1.050) -> list[Candle]:
    """SWING_LOOKBACK+1 velas con un swing high en el índice 5."""
    return _base_candles(swing_high_at=(5, high_level))


def _candles_with_swing_low(low_level: float = 0.950) -> list[Candle]:
    """SWING_LOOKBACK+1 velas con un swing low en el índice 7."""
    return _base_candles(swing_low_at=(7, low_level))


# ── PUT: señal en resistencia con mecha superior ──


def test_reversal_swing_put_at_resistance():
    """R1: vela toca swing high con mecha superior → señal PUT."""
    candles = _candles_with_swing_high(high_level=1.050)
    # Reemplazar última vela: toca swing high con mecha superior grande
    candles[-1] = Candle(
        ts=candles[-1].ts,
        open=1.0,
        high=1.050,  # toca exactamente el swing high
        low=0.998,
        close=1.005,
    )

    result = detect_reversal_swing(candles)

    assert result is not None
    direction, strength = result
    assert direction == "put"
    assert 0.0 < strength <= 1.0


# ── CALL: señal en soporte con mecha inferior ──


def test_reversal_swing_call_at_support():
    """R2: vela toca swing low con mecha inferior → señal CALL."""
    candles = _candles_with_swing_low(low_level=0.950)
    # Reemplazar última vela: toca swing low con mecha inferior grande
    candles[-1] = Candle(
        ts=candles[-1].ts,
        open=1.0,
        high=1.005,
        low=0.950,  # toca exactamente el swing low
        close=0.998,
    )

    result = detect_reversal_swing(candles)

    assert result is not None
    direction, strength = result
    assert direction == "call"
    assert 0.0 < strength <= 1.0


# ── Sin señal: mecha muy pequeña ──


def test_reversal_swing_no_signal_small_wick():
    """R3: toque de swing high pero mecha pequeña → None."""
    candles = _candles_with_swing_high(high_level=1.050)
    # Vela con mecha superior pequeña (ratio < 0.4)
    candles[-1] = Candle(
        ts=candles[-1].ts,
        open=1.040,
        high=1.050,  # toca swing high
        low=1.035,
        close=1.045,
    )
    # upper_wick = 1.050 - 1.045 = 0.005
    # range = 1.050 - 1.035 = 0.015
    # ratio = 0.005 / 0.015 ≈ 0.333 < 0.4

    assert detect_reversal_swing(candles) is None


# ── Sin señal: no hay toque ──


def test_reversal_swing_no_signal_no_touch():
    """R3: swing high presente pero vela no lo toca → None."""
    candles = _candles_with_swing_high(high_level=1.050)
    # Vela que no toca el swing high
    candles[-1] = Candle(
        ts=candles[-1].ts,
        open=1.0,
        high=1.010,  # no toca 1.050
        low=0.995,
        close=1.005,
    )
    # abs(1.050 - 1.010) / 1.050 = 0.038 > 0.001

    assert detect_reversal_swing(candles) is None


# ── Sin señal: sin swings detectados ──


def test_reversal_swing_no_signal_flat_market():
    """R3: sin swing highs ni lows en el lookback → None."""
    candles = _base_candles()  # todas las velas planas

    assert detect_reversal_swing(candles) is None


# ── Sin señal: pocas velas ──


def test_reversal_swing_no_signal_too_few_candles():
    """R3: menos de SWING_LOOKBACK+1 velas → None."""
    candles = [Candle(ts=i * 60, open=1.0, high=1.002, low=0.998, close=1.0)
               for i in range(5)]

    assert detect_reversal_swing(candles) is None
