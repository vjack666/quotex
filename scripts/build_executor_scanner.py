"""Genera executor.py y scanner.py desde el monolito."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
MONOLITH = SRC / "_monolith_backup.py"
if not MONOLITH.exists():
    MONOLITH = SRC / "consolidation_bot.py"
lines = MONOLITH.read_text(encoding="utf-8").splitlines(keepends=True)


def extract_method(name: str, indent: str = "    ") -> str:
    pattern = rf"^{re.escape(indent)}(async )?def {name}\("
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i
            break
    if start is None:
        raise ValueError(f"Method {name} not found")
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(rf"^{re.escape(indent)}(async )?def ", lines[j]) or lines[j].startswith("class "):
            end = j
            break
    return "".join(lines[start:end])


def indent_block(code: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    out = []
    for line in code.splitlines(keepends=True):
        if line.strip():
            out.append(prefix + line)
        else:
            out.append(line)
    return "".join(out)


EXECUTOR_METHODS = [
    "set_session_start_balance",
    "_round_up_to_cents",
    "_compute_initial_amount",
    "_compute_compensation_amount",
    "_get_asset_payout",
    "_get_current_price",
    "_cap_martin_amount",
    "_update_dynamic_threshold",
    "_record_scan_acceptances",
    "_cleanup_asset_blacklist",
    "_is_asset_blacklisted",
    "_register_asset_outcome",
    "_can_enter_asset_now",
    "_register_successful_entry_asset",
    "_current_martin_attempt_limit",
    "_martin_session_available",
    "_track_task",
    "_on_background_task_done",
    "shutdown_background_tasks",
    "_consume_fresh_watched_candidate",
    "_try_enter_martin_now",
    "_monitor_trade_live",
    "_resolve_trade_after_expiry",
    "_process_pending_martin",
    "_reset_cycle",
    "_update_cycle_after_result",
    "refresh_balance_and_risk",
    "reconcile_pending_candidates",
    "_strategy_snapshot",
    "_sync_to_next_candle_open",
    "_resolve_trade",
    "_check_martin",
    "open_trades_get",
    "_enter",
]

SCANNER_EXTRA_METHODS = [
    "_serialize_candles",
    "_broken_capture_file",
    "_write_capture_payload",
    "_record_broken_zone_snapshot",
    "_capture_followup_after_delay",
    "_schedule_followup_capture",
    "_threshold_label",
    "_threshold_change_reason",
    "_build_blacklist_summary_line",
    "_build_ob_summary_line",
    "_build_ma_summary_line",
    "_log_dry_run_verbose_cycle_summary",
    "_process_pending_reversals",
]

executor_header = '''"""Ejecución de órdenes, martingala y gestión de ciclo."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from math import ceil
from typing import TYPE_CHECKING, Any, Deque, List, Optional, Tuple

from config import (
    ADAPTIVE_THRESHOLD_BASE,
    ADAPTIVE_THRESHOLD_HIGH,
    ADAPTIVE_THRESHOLD_LOW,
    ADAPTIVE_THRESHOLD_WINDOW_SCANS,
    ASSET_BLACKLIST_DURATION_MIN,
    ASSET_LOSS_STREAK_LIMIT,
    BROKER_TZ,
    CANDLE_FETCH_1M_TIMEOUT_SEC,
    CYCLE_MAX_OPERATIONS,
    CYCLE_TARGET_PROFIT_PCT,
    CYCLE_TARGET_WINS,
    DURATION_SEC,
    ENTRY_MAX_LAG_SEC,
    ENTRY_REJECT_LAST_SEC,
    ENTRY_SYNC_TO_CANDLE,
    MARTIN_ALERT_PCT,
    MARTIN_LIVE_WINDOW_MAX_SEC,
    MARTIN_LIVE_WINDOW_MIN_SEC,
    MARTIN_LOW_BALANCE_THRESHOLD,
    MARTIN_MAX_ATTEMPTS_LOW_BALANCE,
    MARTIN_MAX_ATTEMPTS_SESSION,
    MARTIN_MAX_PCT_BALANCE,
    MARTIN_MONITOR_INTERVAL_SEC,
    MARTIN_RESOLVE_GRACE_SEC,
    MARTIN_RESOLVE_MAX_ATTEMPTS,
    MARTIN_RESOLVE_RETRY_SEC,
    MARTIN_RESOLVE_TIMEOUT_SEC,
    MAX_CONCURRENT_TRADES,
    MAX_CONSECUTIVE_ENTRIES_PER_ASSET,
    MAX_LOSS_SESSION,
    MIN_ORDER_AMOUNT,
    MIN_PAYOUT,
    PENDING_RECONCILE_AGE_MIN,
    TF_1M,
    TF_5M,
    CANDLES_LOOKBACK,
    MIN_CONSOLIDATION_BARS,
    MAX_RANGE_PCT,
    TOUCH_TOLERANCE_PCT,
    MAX_CONSOLIDATION_MIN,
    SCAN_INTERVAL_SEC,
    COOLDOWN_BETWEEN_ENTRIES,
    VOLUME_MULTIPLIER,
    ZONE_MIN_AGE_MIN,
)
from connection import fetch_candles_with_retry, get_open_assets, place_order
from entry_scorer import CandidateEntry
from models import ConsolidationZone, EntryTimingInfo, MartinPending, TradeState
from strat_a import price_at_ceiling, price_at_floor
from trade_journal import get_journal

if TYPE_CHECKING:
    from pyquotex.stable_api import Quotex

log = logging.getLogger("executor")

'''

executor_body_raw = "\n".join(extract_method(m).rstrip() for m in EXECUTOR_METHODS)
executor_body_raw = executor_body_raw.replace("async def _enter", "async def enter_trade")
executor_body_raw = re.sub(r"await self\._enter\(", "await self.enter_trade(", executor_body_raw)
executor_body_raw = executor_body_raw.replace("self._round_up_to_cents", "self._round_up_to_cents")
executor_body_raw = executor_body_raw.replace("self._sync_to_next_candle_open", "self._sync_to_next_candle_open")
executor_body_raw = executor_body_raw.replace("self._resolve_trade", "self._resolve_trade")
executor_body_raw = executor_body_raw.replace("self._martin_session_available", "self._martin_session_available")
executor_body_raw = executor_body_raw.replace("self._get_asset_payout", "self._get_asset_payout")
executor_body_raw = executor_body_raw.replace("self._compute_compensation_amount", "self._compute_compensation_amount")
executor_body_raw = executor_body_raw.replace("self._cap_martin_amount", "self._cap_martin_amount")
executor_body_raw = executor_body_raw.replace("self._try_enter_martin_now", "self._try_enter_martin_now")
executor_body_raw = executor_body_raw.replace("self._update_cycle_after_result", "self._update_cycle_after_result")
executor_body_raw = executor_body_raw.replace("self._register_asset_outcome", "self._register_asset_outcome")
executor_body_raw = executor_body_raw.replace("self._reset_cycle", "self._reset_cycle")
executor_body_raw = executor_body_raw.replace("self._current_martin_attempt_limit", "self._current_martin_attempt_limit")
executor_body_raw = executor_body_raw.replace("self._can_enter_asset_now", "self._can_enter_asset_now")
executor_body_raw = executor_body_raw.replace("self._register_successful_entry_asset", "self._register_successful_entry_asset")
executor_body_raw = executor_body_raw.replace("self._track_task", "self._track_task")
executor_body_raw = executor_body_raw.replace("self._resolve_trade_after_expiry", "self._resolve_trade_after_expiry")
executor_body_raw = executor_body_raw.replace("self._monitor_trade_live", "self._monitor_trade_live")

# State on bot
state_attrs = [
    "session_start_balance", "current_balance", "martingale", "cycle_start_balance",
    "accepted_scans_window", "current_score_threshold", "asset_blacklist_until",
    "asset_loss_streaks", "last_entry_asset", "last_entry_asset_streak",
    "stats", "_trade_tasks", "_followup_capture_tasks", "watched_candidates",
    "pending_martin", "trades", "zones", "compensation_pending", "last_closed_amount",
    "last_closed_outcome", "session_stop_hit", "cycle_id", "cycle_ops", "cycle_wins",
    "cycle_losses", "cycle_profit", "dry_run", "account_type", "last_known_price",
]
for attr in state_attrs:
    executor_body_raw = re.sub(rf"\bself\.{attr}\b", f"self.bot.{attr}", executor_body_raw)

executor_code = (
    executor_header
    + "class TradeExecutor:\n"
    + "    def __init__(self, client, bot):\n"
    + "        self.client = client\n"
    + "        self.bot = bot\n\n"
    + executor_body_raw
)
executor_code = executor_code.replace("await await ", "await ")
(SRC / "executor.py").write_text(executor_code, encoding="utf-8")
print(f"executor.py: {len(executor_code.splitlines())} lines")

scanner_header = '''"""Descarga de velas y recolección de candidatos por activo."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from candle_patterns import detect_reversal_pattern, explain_no_pattern_reason
from config import (
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
    FORCE_EXECUTE_STRONG_BREAKOUT,
    H1_CANDLES_LOOKBACK,
    H1_CONFIRM_ENABLED,
    H1_FETCH_TIMEOUT_SEC,
    H1_TF_SEC,
    MAX_CONCURRENT_TRADES,
    MAX_CONSOLIDATION_MIN,
    MIN_CONSOLIDATION_BARS,
    MIN_PAYOUT,
    ORDER_BLOCK_CANDLES,
    ORDER_BLOCK_TF_SEC,
    REBOUND_MIN_STRENGTH_CALL,
    REJECTION_CANDLE_MIN_BODY,
    SCAN_MAX_ASSETS_PER_CYCLE,
    SCAN_PROGRESS_EVERY,
    STRICT_PATTERN_CHECK,
    TF_5M,
    ZONE_AGE_BREAKOUT_MIN,
    ZONE_AGE_REBOUND_MIN,
    ZONE_MIN_AGE_MIN,
)
from connection import fetch_candles_with_retry, get_open_assets
from loop_utils import sleep_with_inline_countdown
from entry_scorer import CandidateEntry, explain_score, score_candidate, select_best
from models import Candle, ConsolidationZone, PendingReversal
from strat_a import (
    broke_above,
    broke_below,
    compute_dynamic_range,
    compute_ma_state,
    detect_consolidation,
    detect_order_blocks,
    infer_h1_trend,
    is_high_volume_break,
    is_put_pattern_blacklisted,
    price_at_ceiling,
    price_at_floor,
    required_rebound_strength,
    score_ma,
    score_order_blocks,
    validate_rejection_candle,
)
from strat_support import find_strong_support_2m
from trade_journal import get_journal

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

'''

scanner_extra = "\n".join(extract_method(m).rstrip() for m in SCANNER_EXTRA_METHODS)
scanner_extra = scanner_extra.replace("@staticmethod\n\n", "@staticmethod\n")
scanner_extra = scanner_extra.replace("async def _capture_followup", "async def _capture_followup")

scan_all = extract_method("scan_all").rstrip()

# transforms
replacements = [
    ("self._enter(", "await self.executor.enter_trade("),
    ("self._compute_initial_amount", "self.executor._compute_initial_amount"),
    ("self._compute_compensation_amount", "self.executor._compute_compensation_amount"),
    ("self.refresh_balance_and_risk", "self.executor.refresh_balance_and_risk"),
    ("self._check_martin", "self.executor._check_martin"),
    ("self._process_pending_martin", "self.executor._process_pending_martin"),
    ("self._update_dynamic_threshold", "self.executor._update_dynamic_threshold"),
    ("self._record_scan_acceptances", "self.executor._record_scan_acceptances"),
    ("self._strategy_snapshot", "self.executor._strategy_snapshot"),
    ("self._cleanup_asset_blacklist", "self.executor._cleanup_asset_blacklist"),
    ("self._is_asset_blacklisted", "self.executor._is_asset_blacklisted"),
    ("self._required_rebound_strength", "required_rebound_strength"),
    ("self._is_put_pattern_blacklisted", "is_put_pattern_blacklisted"),
    ("self._validate_rejection_candle", "validate_rejection_candle"),
    ("self._detect_order_blocks", "detect_order_blocks"),
    ("self._score_order_blocks", "score_order_blocks"),
    ("self._score_ma", "score_ma"),
]
for old, new in replacements:
    scan_all = scan_all.replace(old, new)

state_attrs_scanner = [
    "client", "dry_run", "zones", "broken_zones", "trades", "stats", "compensation_pending",
    "last_closed_amount", "last_closed_outcome", "watched_candidates", "capture_dir",
    "_followup_capture_tasks", "last_known_price", "failed_assets", "pending_reversals",
    "pending_martin", "accepted_scans_window", "current_score_threshold",
    "order_blocks_by_asset", "ma_state_by_asset", "greylist_assets", "account_type",
]
for attr in state_attrs_scanner:
    scan_all = re.sub(rf"\bself\.{attr}\b", f"self.bot.{attr}", scan_all)

scan_all = scan_all.replace(
    """                dynamic_max_range = MAX_RANGE_PCT
                atr_pct = 0.0
                if USE_DYNAMIC_ATR_RANGE:
                    atr = compute_atr(candles, ATR_PERIOD)
                    mid = candles[-1].close if candles[-1].close > 0 else 0.0
                    if atr > 0 and mid > 0:
                        atr_pct = atr / mid
                        dynamic_max_range = _clamp(
                            atr_pct * ATR_RANGE_FACTOR,
                            MIN_DYNAMIC_RANGE_PCT,
                            MAX_DYNAMIC_RANGE_PCT,
                        )
                dynamic_touch_tolerance = TOUCH_TOLERANCE_PCT
                if atr_pct > 0:
                    dynamic_touch_tolerance = _clamp(atr_pct * 0.12, 0.00015, 0.00080)""",
    "                dynamic_max_range, atr_pct, dynamic_touch_tolerance = compute_dynamic_range(candles)",
)

# ma_state helper inside scanner
ma_helper = '''
    def _compute_ma_state(self, asset: str, candles_5m: List[Candle]):
        prev = self.bot.ma_state_by_asset.get(asset)
        state = compute_ma_state(candles_5m, prev)
        if state is not None:
            self.bot.ma_state_by_asset[asset] = state
        return state

'''

scanner_code = scanner_header + ma_helper + scanner_extra + "\n" + scan_all
scanner_code = scanner_code.replace("await await ", "await ")
(SRC / "scanner.py").write_text(scanner_code, encoding="utf-8")
print(f"scanner.py: {len(scanner_code.splitlines())} lines")