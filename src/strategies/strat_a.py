"""Compatibility entry point for Strategy A.

Canonical implementation remains in ``src/strat_a.py`` until its shared
candle/config/model dependencies are migrated. New code should import from
this namespace so the strategy can be moved without another API change.
"""
from strat_a import *  # noqa: F401,F403
