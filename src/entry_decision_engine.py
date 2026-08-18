"""Compatibility shim for the relocated decision engine.

The implementation now lives in ``src/decision/entry_decision_engine.py``.
This module remains temporarily so existing imports keep working while the
repository is being reorganized.
"""

from decision.entry_decision_engine import *  # noqa: F401,F403
from decision.entry_decision_engine import (
    _check_candles_available,
    _check_no_active_trade,
    _check_cycle_limit,
    _check_payout_minimum,
    _check_score_minimum,
    _check_spike_1m,
    _check_spike_5m,
    _check_htf_available_and_aligned,
    _check_pattern_confirmed,
    _check_zone_age_minimum,
)
