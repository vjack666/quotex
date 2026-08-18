"""Execution configuration access boundary.

Keep live/hot-reloaded settings behind this module. The legacy config module
remains the source of truth; this wrapper prevents new execution code from
spreading configuration imports across the package.
"""
from __future__ import annotations
import config as _cfg


def live_duration_sec(default: int = 300) -> int:
    return int(getattr(_cfg, "DURATION_SEC", default))


def max_concurrent_trades(default: int = 1) -> int:
    return int(getattr(_cfg, "MAX_CONCURRENT_TRADES", default))


__all__ = ["live_duration_sec", "max_concurrent_trades"]
