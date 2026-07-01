"""Estrategia momentum 1m: cuerpo grande + cierre en tercio extremo."""
from __future__ import annotations

from statistics import mean
from typing import Optional

from models import Candle

MOMENTUM_LOOKBACK = 10
MOMENTUM_MIN_BODY_RATIO = 1.5
MOMENTUM_UPPER_THIRD = 2.0 / 3.0
MOMENTUM_LOWER_THIRD = 1.0 / 3.0


def detect_momentum_1m(candles: list[Candle]) -> Optional[tuple[str, float]]:
    """
    Detecta momentum en la última vela 1m.

    Returns:
        (direction, strength) con direction en {"call", "put"} y strength en [0, 1],
        o None si no hay señal válida.
    """
    if len(candles) < MOMENTUM_LOOKBACK + 1:
        return None

    last = candles[-1]
    lookback = candles[-(MOMENTUM_LOOKBACK + 1):-1]
    avg_body = mean(c.body for c in lookback) or 0.0
    if avg_body <= 0:
        return None

    body_ratio = last.body / avg_body
    if body_ratio < MOMENTUM_MIN_BODY_RATIO:
        return None

    candle_range = last.range
    if candle_range <= 0:
        return None

    close_pos = (last.close - last.low) / candle_range
    strength = min(1.0, (body_ratio - MOMENTUM_MIN_BODY_RATIO) / 1.0)

    if last.close > last.open and close_pos >= MOMENTUM_UPPER_THIRD:
        return ("call", round(strength, 4))

    if last.close < last.open and close_pos <= MOMENTUM_LOWER_THIRD:
        return ("put", round(strength, 4))

    return None