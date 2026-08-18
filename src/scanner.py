"""Descarga de velas y recolección de candidatos por activo."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from bot_logging import asset_detail, format_reject_summary, is_verbose, short_reason
from candle_patterns import detect_reversal_pattern, explain_no_pattern_reason, last_closed_shape
import config as _runtime_config
from config import (
    ADAPTIVE_THRESHOLD_HIGH,
    ADAPTIVE_THRESHOLD_LOW,
    ADAPTIVE_THRESHOLD_WINDOW_SCANS,
    BROKEN_FOLLOWUP_1M_COUNT,
    BROKEN_FOLLOWUP_DELAY_SEC,
    BROKER_TZ,
    CANDLE_FETCH_1M_TIMEOUT_SEC,
    CANDLE_FETCH_TIMEOUT_SEC,
    CANDLES_LOOKBACK,
    CANDLE_FETCH_CONCURRENCY,
    COOLDOWN_BETWEEN_ENTRIES,
    DRY_RUN_VERBOSE,
    DURATION_SEC,
    EDIFICIO_BRAKE_CONFIRM_RATIO,
    H1_CANDLES_LOOKBACK,
    H1_FETCH_TIMEOUT_SEC,
    H1_TF_SEC,
    MAX_CONCURRENT_TRADES,
    MAX_CONSOLIDATION_MIN,
    MIN_CONSOLIDATION_BARS,
    MIN_PAYOUT,

    REBOUND_MIN_STRENGTH_CALL,
    REBOUND_MIN_STRENGTH_PUT,
    REJECTION_CANDLE_MIN_BODY,
    SCAN_MAX_ASSETS_PER_CYCLE,
    SCAN_PHASE_LOG,
    SCAN_PROGRESS_EVERY,

    STRAT_A_MIN_PAYOUT,
    STRAT_A_MIN_SCORE,
    STRAT_F_MIN_SCORE,
    STRAT_A_RADAR_ENABLED,
    STRAT_A_RADAR_MIN_READINESS,
    STRAT_A_ZONE_MIN_AGE_REBOUND,
    STRAT_MOMENTUM_ENABLED,
    STRAT_F_ENABLED,
    STRAT_F_ONLY,
    STRAT_ORDER_BLOCK_ENABLED,
    STRAT_ORDER_BLOCK_MIN_STRENGTH,
    TF_1M,
    TF_5M,
    ZONE_AGE_BREAKOUT_MIN,
    ZONE_AGE_REBOUND_MIN,
    ZONE_MIN_AGE_MIN,
)
from connection import fetch_candles_with_retry, get_open_assets
from loop_utils import get_scan_pool, shutdown_scan_pool, init_scan_pool, diagnose_scan_pool_broken
from concurrent.futures.process import BrokenProcessPool
from black_box_recorder import get_black_box
from stochastic_m15 import compute_stoch
from stochastic_zones import apply_stoch_help
from decision.entry_decision_engine import (
    _check_htf_available_and_aligned,
)
from data.scan_prefetch import (
    ScanCycleData,
    decrement_failed_assets,
    prefetch_primary_candles,
    prefetch_strat_a_secondary,
    symbols_needing_strat_a_prefetch,
)
from loop_utils import sleep_with_inline_countdown
