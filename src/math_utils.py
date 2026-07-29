"""math_utils — Funciones matemáticas compartidas.

Centraliza utilidades que estaban duplicadas en 3-4 archivos cada una.
"""

from statistics import mean
from typing import Any, List, Sequence


def clamp(val: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, val))


def ema(values: Sequence[float], period: int) -> List[float]:
    """Exponential moving average over the full series.

    Returns empty list if len(values) < period.
    First element = mean of first `period` values.
    """
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    result: List[float] = [mean(values[:period])]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def normalize(val: float, lo: float, hi: float) -> float:
    """Normalize val to 0-1 range, clamped.

    Returns 0.0 when hi <= lo (degenerate range).
    """
    if hi <= lo:
        return 0.0
    return clamp((val - lo) / (hi - lo), 0.0, 1.0)


def fractal_up(candles: List[Any], i: int) -> bool:
    """Fractal alcista (techo): máximo central más alto que los 2 a cada lado."""
    if i < 2 or i > len(candles) - 3:
        return False
    h = candles[i].high
    return (
        h > candles[i - 1].high
        and h > candles[i - 2].high
        and h > candles[i + 1].high
        and h > candles[i + 2].high
    )


def fractal_down(candles: List[Any], i: int) -> bool:
    """Fractal bajista (suelo): mínimo central más bajo que los 2 a cada lado."""
    if i < 2 or i > len(candles) - 3:
        return False
    lo = candles[i].low
    return (
        lo < candles[i - 1].low
        and lo < candles[i - 2].low
        and lo < candles[i + 1].low
        and lo < candles[i + 2].low
    )
