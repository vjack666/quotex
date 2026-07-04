"""Estrategia reversal swing: reversión en niveles dinámicos de soporte/resistencia."""
from __future__ import annotations

from statistics import mean
from typing import Optional

from models import Candle

SWING_LOOKBACK = 12
MAX_SWINGS = 5
PROXIMITY_TOLERANCE = 0.001
MIN_WICK_RATIO = 0.4
MIN_STRENGTH = 0.3


def detect_reversal_swing(candles_1m: list[Candle]) -> Optional[tuple[str, float]]:
    """
    Detecta reversión en niveles de soporte/resistencia dinámicos (swing highs/lows).

    Returns:
        (direction, strength) con direction en {"call", "put"} y strength en [0, 1],
        o None si no hay señal válida.
    """
    if len(candles_1m) < SWING_LOOKBACK + 1:
        return None

    lookback = candles_1m[-(SWING_LOOKBACK + 1):-1]
    last = candles_1m[-1]

    # Detectar swing highs y swing lows en la ventana lookback
    swing_highs: list[float] = []
    swing_lows: list[float] = []

    for i in range(1, len(lookback) - 1):
        if lookback[i].high > lookback[i - 1].high and lookback[i].high > lookback[i + 1].high:
            swing_highs.append(lookback[i].high)
        if lookback[i].low < lookback[i - 1].low and lookback[i].low < lookback[i + 1].low:
            swing_lows.append(lookback[i].low)

    # Mantener solo los últimos MAX_SWINGS
    swing_highs = swing_highs[-MAX_SWINGS:]
    swing_lows = swing_lows[-MAX_SWINGS:]

    candle_range = last.range
    if candle_range <= 0:
        return None

    upper_wick = last.high - max(last.open, last.close)
    lower_wick = min(last.open, last.close) - last.low

    # ── PUT: toque de resistencia con mecha superior ──
    if upper_wick > 0:
        upper_wick_ratio = upper_wick / candle_range
        for level in reversed(swing_highs):
            if abs(level - last.high) / level <= PROXIMITY_TOLERANCE:
                if upper_wick_ratio >= MIN_WICK_RATIO:
                    avg_upper = mean(
                        max(c.high - max(c.open, c.close), 0.001)
                        for c in lookback
                    )
                    raw_strength = min(upper_wick / avg_upper, 2.0)
                    strength = min(raw_strength, 1.0)
                    if strength >= MIN_STRENGTH:
                        return ("put", round(strength, 4))
                break

    # ── CALL: toque de soporte con mecha inferior ──
    if lower_wick > 0:
        lower_wick_ratio = lower_wick / candle_range
        for level in reversed(swing_lows):
            if abs(level - last.low) / level <= PROXIMITY_TOLERANCE:
                if lower_wick_ratio >= MIN_WICK_RATIO:
                    avg_lower = mean(
                        max(min(c.open, c.close) - c.low, 0.001)
                        for c in lookback
                    )
                    raw_strength = min(lower_wick / avg_lower, 2.0)
                    strength = min(raw_strength, 1.0)
                    if strength >= MIN_STRENGTH:
                        return ("call", round(strength, 4))
                break

    return None
