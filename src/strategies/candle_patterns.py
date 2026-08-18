"""Compatibility entry point for candle pattern analysis used by strategies.

Canonical implementation remains in ``src/candle_patterns.py`` while shared
model dependencies are being separated. New strategy code may import from
``strategies.candle_patterns``.
"""
from candle_patterns import *  # noqa: F401,F403
