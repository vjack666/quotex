"""Pure adaptive score-threshold calculation."""
from __future__ import annotations
from collections.abc import Sequence


def calculate_threshold(window: Sequence[int], base: int, low: int, high: int, required: int) -> int:
    if len(window) < required:
        return int(base)
    accepted = sum(max(0, int(v)) for v in window)
    if accepted == 0:
        return int(low)
    if accepted > 2:
        return int(high)
    return int(base)

__all__ = ["calculate_threshold"]
