"""Constantes operativas del bot de consolidación Quotex."""
from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

TF_5M = 300
TF_15M = 900
TF_1M = 60
CANDLES_LOOKBACK = 55
MIN_CONSOLIDATION_BARS = 12
MAX_RANGE_PCT = 0.003
TOUCH_TOLERANCE_PCT = 0.00035
MAX_CONSOLIDATION_MIN = 0
MIN_PAYOUT = 80  # web → min_payout (Bankroll card); fallback primer arranque
DURATION_SEC = 300  # expiración de la orden: 5 min (antes 180s = 3 min)
SCAN_INTERVAL_SEC = 60
CONNECT_RETRIES = 3
MAX_CONCURRENT_TRADES = 1
COOLDOWN_BETWEEN_ENTRIES = 30
ENTRY_SYNC_TO_CANDLE = True
ENTRY_MAX_LAG_SEC = 0.3
ENTRY_REJECT_LAST_SEC = 2.0
ALIGN_SCAN_TO_CANDLE = False
SCAN_LEAD_SEC = 35.0
MAX_LOSS_SESSION = 0.20

CYCLE_MAX_OPERATIONS = 5
CYCLE_TARGET_WINS = 3
CYCLE_TARGET_PROFIT_PCT = 0.10

# =============================================================================
# BANKROLL MASSANIELLO — incógnitas rellenadas desde la WEB
# -----------------------------------------------------------------------------
# Fuente de verdad: pestaña Operación → card "Bankroll binarias" → Guardar.
# Persistido en: data/hub_bankroll.json
#
# NO edites estos números a mano para operar en demo: usá el hub.
# Los valores de abajo son SOLO fallback de primer arranque (si nunca guardaste).
# Al importar este módulo se hidratan desde hub_bankroll.json si existe.
# =============================================================================
MASSANIELLO_OPERATIONS = 5              # web → massaniello_ops
MASSANIELLO_EXPECTED_WINS = 3           # web → massaniello_wins  (ITM objetivo)
SESSION_MAX_MIN = 60                    # web → session_max_min
SESSION_COOLDOWN_MINUTES = 0  # Minutes to wait between cycles (0 = immediate)
RISK_MANAGER = "massaniello"
# Capital de riesgo asignado a binarias (no el balance completo de la cuenta).
# web → massaniello_virtual_capital. Si > 0, Massaniello dimensiona sobre esto.
MASSANIELLO_VIRTUAL_CAPITAL = 30.0

USE_DYNAMIC_ATR_RANGE = True
ATR_PERIOD = 14
ATR_RANGE_FACTOR = 1.35
MIN_DYNAMIC_RANGE_PCT = 0.0015
MAX_DYNAMIC_RANGE_PCT = 0.0150

H1_CONFIRM_ENABLED = True
H1_TF_SEC = 3600
H1_CANDLES_LOOKBACK = 80
H1_EMA_FAST = 20
H1_EMA_SLOW = 50
H1_FETCH_TIMEOUT_SEC = 12.0
CANDLE_FETCH_TIMEOUT_SEC = 8.0
CANDLE_FETCH_1M_TIMEOUT_SEC = 12.0
FETCH_RETRIES = 2
FETCH_RETRY_BACKOFF_SEC = 0.35
ORDER_SEND_RETRIES = 1
RECONNECT_TIMEOUT_SEC = 12.0
SCAN_MAX_ASSETS_PER_CYCLE = 40
# Logging verbosity: set BOT_LOG_VERBOSE=1 for per-asset noise + phase markers.
# Default (normal) keeps cycle summaries, signals, entries, wins/losses.
LOG_VERBOSE = os.environ.get("BOT_LOG_VERBOSE", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
SCAN_PROGRESS_EVERY = 10 if LOG_VERBOSE else 0  # 0 = no progress spam
SCAN_WS_INTER_ASSET_DELAY_SEC = 2.0
SCAN_PHASE_LOG = bool(LOG_VERBOSE)  # [FASE n/5] only in verbose
CONNECT_RETRY_DELAY_SEC = 2.0

CANDLE_FETCH_CONCURRENCY = 5
CANDLE_CACHE_TTL_SEC = 300
CANDLE_CACHE_INCREMENTAL_COUNT = 8
HEALTHCHECK_RECONNECT_RETRIES = 2
CF_403_BACKOFF_SEC = 8.0

VOLUME_MULTIPLIER = 1.2
VOLUME_LOOKBACK = 10
REBOUND_MIN_STRENGTH_CALL = 0.50
REBOUND_MIN_STRENGTH_PUT = 0.65
REJECTION_CANDLE_MIN_BODY = 0.40
REJECTION_PUT_MIN_UPPER_WICK = 0.30
ZONE_AGE_REBOUND_MIN = 20
ZONE_AGE_BREAKOUT_MIN = 8
ZONE_MIN_AGE_MIN = ZONE_AGE_REBOUND_MIN
FORCE_EXECUTE_STRONG_BREAKOUT = True
# Glitch guard for zone BROKEN_* (OTC bad ticks). Conservative: only blocks
# absurd jumps (e.g. 93→83). Normal breakouts stay valid.
# gap 2.5% vs previous close OR close farther than 5 zone-widths past edge.
ZONE_BREAK_MAX_GAP_PCT = 0.025
ZONE_BREAK_MAX_ZONE_WIDTHS = 5.0
GREYLIST_ASSETS = {"USDDZD_otc"}
PATTERN_PUT_BLACKLIST = {"bearish_engulfing"}
STRICT_PATTERN_CHECK = True

ADAPTIVE_THRESHOLD_BASE = 65
ADAPTIVE_THRESHOLD_LOW = 62
ADAPTIVE_THRESHOLD_HIGH = 68
ADAPTIVE_THRESHOLD_WINDOW_SCANS = 10

ASSET_LOSS_STREAK_LIMIT = 3
ASSET_BLACKLIST_DURATION_MIN = 60
MAX_CONSECUTIVE_ENTRIES_PER_ASSET = 2

ORDER_BLOCK_LOOKBACK = 50
ORDER_BLOCK_MAX_PER_SIDE = 3
ORDER_BLOCK_MIN_MOVE_PCT = 0.002
ORDER_BLOCK_TOUCH_TOLERANCE_PCT = 0.0003
ORDER_BLOCK_TF_SEC = 180
ORDER_BLOCK_CANDLES = 55

MA_LOOKBACK_CANDLES = 60
MA_FAST_PERIOD = 35
MA_SLOW_PERIOD = 50
MA_FLAT_DELTA_PCT = 0.0005
DRY_RUN_VERBOSE = bool(LOG_VERBOSE)

EMAIL = os.environ.get("QUOTEX_EMAIL", "")
PASSWORD = os.environ.get("QUOTEX_PASSWORD", "")

BROKER_TZ = timezone(timedelta(hours=-3))
BROKER_TZ_LABEL = "UTC-3"

MIN_ORDER_AMOUNT = 1.00
MARTIN_MAX_PCT_BALANCE = 0.20
MARTIN_MAX_ATTEMPTS_SESSION = 2
MARTIN_LOW_BALANCE_THRESHOLD = 100.0
MARTIN_MAX_ATTEMPTS_LOW_BALANCE = 3
PENDING_RECONCILE_AGE_MIN = 15.0
MARTIN_MONITOR_INTERVAL_SEC = 10.0
MARTIN_ALERT_PCT = 0.0005
MARTIN_LIVE_WINDOW_MIN_SEC = 30.0
MARTIN_LIVE_WINDOW_MAX_SEC = 60.0
# Resolve timing: Quotex often settles a few seconds AFTER nominal expiry.
# check_win waits until game_state==1; short timeouts caused premature LOSS
# when profitAmount was still 0 / history not updated yet.
MARTIN_RESOLVE_GRACE_SEC = 20.0
MARTIN_RESOLVE_TIMEOUT_SEC = 90.0
MARTIN_RESOLVE_RETRY_SEC = 8.0
MARTIN_RESOLVE_MAX_ATTEMPTS = 6

# Aligned to MIN_PAYOUT when hub saves bankroll (same floor for all strats).
STRAT_A_MIN_PAYOUT = 87
STRAT_A_MIN_SCORE = 75
STRAT_A_ZONE_MIN_AGE_REBOUND = 30

STRAT_A_ONLY = False
STRAT_A_RADAR_ENABLED = False
STRAT_A_RADAR_MAX_WATCH = 5
STRAT_A_RADAR_MIN_READINESS = 70.0
STRAT_A_RADAR_MIN_AGE_RATIO = 0.75
STRAT_A_RADAR_TICK_SEC = 60
STRAT_A_RADAR_FULL_SCAN_MIN_SEC = 180
STRAT_MOMENTUM_ENABLED = False

# STRAT-F (Fractal / Wyckoff) — marco M15/M5/M1
STRAT_F_ENABLED = True
STRAT_F_ONLY = True  # opera SOLO STRAT-F (ignora STRAT-A/MOMENTUM/SWING/OB)
STRAT_F_MIN_PAYOUT = 80  # overridden by web min_payout on Guardar bankroll
STRAT_F_MIN_SCORE = 60
STRAT_F_ZONE_MIN_AGE = 3  # velas M5 minimas de antiguedad de la banda/zona antes de operar

STRAT_ORDER_BLOCK_ENABLED = False
STRAT_ORDER_BLOCK_MIN_STRENGTH = 30
STRAT_REVERSAL_SWING_ENABLED = False
STRAT_REVERSAL_SWING_SWING_LOOKBACK = 12
STRAT_REVERSAL_SWING_MAX_SWINGS = 5
STRAT_REVERSAL_SWING_PROXIMITY_TOLERANCE = 0.001
STRAT_REVERSAL_SWING_MIN_WICK_RATIO = 0.4
STRAT_REVERSAL_SWING_MIN_STRENGTH = 0.3

BROKEN_CAPTURE_DIR = Path(__file__).resolve().parent.parent / "data" / "vela_ops"
BROKEN_FOLLOWUP_DELAY_SEC = 15 * 60
BROKEN_FOLLOWUP_1M_COUNT = 40

# Diversification
MAX_SIMULTANEOUS_TRADES = 3
MIN_ASSET_SPREAD = 2
MAX_ENTRIES_PER_ASSET = 1

# Compatibilidad con main.py (_apply_runtime_config)
AMOUNT_INITIAL = 1.0
AMOUNT_MARTIN = 3.0


def _hydrate_bankroll_from_web() -> None:
    """Fill bankroll unknowns from data/hub_bankroll.json (written by the hub)."""
    global MASSANIELLO_OPERATIONS, MASSANIELLO_EXPECTED_WINS
    global MASSANIELLO_VIRTUAL_CAPITAL, SESSION_MAX_MIN, MIN_PAYOUT
    global STRAT_A_MIN_PAYOUT, STRAT_F_MIN_PAYOUT
    try:
        # Local import: hub_bankroll_store must not import config at module level
        from hub_bankroll_store import load_bankroll

        data = load_bankroll()
        if not data:
            return
        if "massaniello_ops" in data:
            MASSANIELLO_OPERATIONS = int(data["massaniello_ops"])
        if "massaniello_wins" in data:
            MASSANIELLO_EXPECTED_WINS = int(data["massaniello_wins"])
        if "massaniello_virtual_capital" in data:
            MASSANIELLO_VIRTUAL_CAPITAL = float(data["massaniello_virtual_capital"])
        if "session_max_min" in data:
            SESSION_MAX_MIN = int(data["session_max_min"])
        if "min_payout" in data:
            MIN_PAYOUT = max(50, min(98, int(data["min_payout"])))
            STRAT_A_MIN_PAYOUT = MIN_PAYOUT
            STRAT_F_MIN_PAYOUT = MIN_PAYOUT
    except Exception:
        # First boot / tests without data dir — keep fallbacks
        pass


_hydrate_bankroll_from_web()