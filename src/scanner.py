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
from scan_prefetch import (
    ScanCycleData,
    decrement_failed_assets,
    prefetch_primary_candles,
    prefetch_strat_a_secondary,
    symbols_needing_strat_a_prefetch,
)
from loop_utils import sleep_with_inline_countdown
from diversification_enforcer import DiversificationEnforcer
from edificio_executor import execute_contratados, is_sticky_cross, resolve_contratados
from entry_scorer import CandidateEntry, explain_score, score_candidate, select_best
from models import Candle, ConsolidationZone, PendingReversal, SignalMode
from strat_a import (
    compute_dynamic_range,
    compute_ma_state,
    detect_consolidation,
    evaluate_strat_a,
    infer_h1_trend,
    is_put_pattern_blacklisted,
    PendingReversalHint,
    price_at_ceiling,
    price_at_floor,
    required_rebound_strength,
    StratAEvaluation,
    validate_rejection_candle,
)
from strat_a_radar import (
    RadarWatchEntry,
    compute_readiness,
    rank_and_trim,
    should_watch,
)
from strat_support import find_strong_support_2m
from strat_momentum import detect_momentum_1m
from strat_fractal import (
    evaluate_strat_f, StratFEvaluation,
    recheck_m15_alignment, stoch_m5_exhausted, extreme_read_gate,
)
from strat_order_block import detect_order_block_entry
from strat_reversal_swing import detect_reversal_swing
from maturing_watchlist import (
    direction_from_m5_event,
    fractal_band_and_age,
    is_r3_young_skip,
    normalize_mode,
    parse_bars_age_from_skip,
)
from trade_journal import get_journal
from zone_ia import ZoneIA
from ml_features import extract_features
from ml_scorer import MLScorer
from multi_tf_correlation import compute_confluence_bonus
from session_awareness import detect_session, get_effective_min_score, should_block, get_current_session_info

if TYPE_CHECKING:
    from executor import TradeExecutor

log = logging.getLogger("scanner")


@dataclass
class ScanResult:
    candidates: list[CandidateEntry] = field(default_factory=list)
    stats_delta: dict[str, int] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


class AssetScanner:
    def __init__(self, bot: Any, executor: "TradeExecutor"):
        self.bot = bot
        self.executor = executor

    @staticmethod
    def _phase_log(phase: str, detail: str) -> None:
        if SCAN_PHASE_LOG:
            log.info("[FASE %s] %s", phase, detail)

    @staticmethod
    def _radar_enabled() -> bool:
        return bool(_runtime_config.STRAT_A_ONLY or STRAT_A_RADAR_ENABLED)

    @staticmethod
    def _is_strat_a_candidate(candidate: CandidateEntry) -> bool:
        return getattr(candidate, "_strategy_origin", "STRAT-A") == "STRAT-A"

    @staticmethod
    def _score_threshold_for_candidate(
        candidate: CandidateEntry,
        session_threshold: int,
    ) -> int:
        origin = getattr(candidate, "_strategy_origin", "STRAT-A")
        if origin == "STRAT-A":
            return STRAT_A_MIN_SCORE
        if origin == "STRAT-F":
            return STRAT_F_MIN_SCORE
        return session_threshold

    @staticmethod
    def _log_strat_a_pattern_veto(sym: str, ev: StratAEvaluation) -> None:
        side = "techo" if ev.entry_mode == "rebound_ceiling" else "piso"
        if ev.skip_reason == "pattern_missing":
            asset_detail(
                log,
                "⛔ [STRAT-A] %s: rebote %s — sin patrón 1m confirmado",
                sym,
                side,
            )
        elif ev.skip_reason == "pattern_insufficient":