"""Feature extraction for the Entry Intelligence Agent (LightGBM scorer).

Pure functions, no I/O. Two feature families:

1. DERIVED / STOCHASTIC (legacy, kept for backward compat with old DB rows):
   math_quality, score_breakdown, spring_margin, stoch M15 plus the
   signal context (direction, payout, duration).

2. GEOMETRY / OHLC WAVE (new, user requirement 2026-07-24):
   The model must DISCOVER patterns on its own — no hand-coded rules.
   We feed it the RAW candle geometry of the pre-entry window plus the
   stochastic across the 3 timeframes, computed OFFLINE from the
   ``candles_1m/5m/15m`` snapshots already stored in ``scan_candidates``.

The ONLY technical indicator is stochastic (M15/M5/M1, already captured).
Everything else is mathematics/geometry of the OHLC bars: body direction,
body ratio, opposing-wick ratio, entry-extreme position, pre-trend slope,
compression, fractal alignment. No RSI/ADX/ATR/Bollinger.
"""

from __future__ import annotations

import json
import math
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
#  FEATURE NAMES (canonical, ordered)
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_NAMES: list[str] = [
    # ── Math quality (5) ── derived from closes
    "math_hurst",
    "math_r_squared",
    "math_angle_deg",
    "math_squeeze",
    "math_composite",
    # ── Stochastic (3 timeframes) ── the ONLY technical indicator
    "stoch_m15_zone",
    "stoch_m5_zone",
    "stoch_m1_zone",
    # ── Wyckoff / spring ──
    "spring_margin",
    # ── Score breakdown (legacy derived) ──
    "score_compression",
    "score_bounce",
    "score_fractal",
    "score_context",
    "score_payout",
    "score_stoch_help",
    # ── OHLC geometry / wave (7) — computed OFFLINE from raw candles ──
    "body_dir",
    "body_ratio",
    "opp_wick_ratio",
    "entry_extreme_pos",
    "pre_trend_slope",
    "compression_geom",
    "fractal_align",
    # ── Signal context (6) ──
    "direction",
    "payout",
    "duration_sec",
    "hour_utc",
    "dow",
    "asset_id",
]

_REQUIRED = set(FEATURE_NAMES)

# Zone label to integer mapping
_ZONE_MAP: dict[str, int] = {
    "Z1": 1,
    "Z2": 2,
    "Z3": 3,
    "Z4": 4,
    "Z5": 5,
}


# ─────────────────────────────────────────────────────────────────────────────
#  Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────
def _encode_zone(raw: Any) -> float:
    """Encode a stochastic zone label (Z1–Z5) to int 1–5. Returns 0 for unknown."""
    if raw is None:
        return 0.0
    key = str(raw).upper().strip()
    return float(_ZONE_MAP.get(key, 0))


def _candle_ohlc(c: Any) -> tuple[float, float, float, float]:
    """Extract (open, high, low, close) from a Candle object or a dict.

    Accepts flexible key naming (open/high/low/close or o/h/l/c).
    Returns (nan-safe) zeros if not parseable.
    """
    if c is None:
        return (0.0, 0.0, 0.0, 0.0)
    try:
        if isinstance(c, dict):
            o = float(c.get("open", c.get("o", 0.0)))
            h = float(c.get("high", c.get("h", 0.0)))
            l = float(c.get("low", c.get("l", 0.0)))
            cc = float(c.get("close", c.get("c", 0.0)))
        else:
            o = float(getattr(c, "open", 0.0))
            h = float(getattr(c, "high", 0.0))
            l = float(getattr(c, "low", 0.0))
            cc = float(getattr(c, "close", 0.0))
        return (o, h, l, cc)
    except (TypeError, ValueError):
        return (0.0, 0.0, 0.0, 0.0)


def _linreg_slope(values: list[float]) -> float:
    """Normalized linear-regression slope of a series.

    Returns slope scaled by mean magnitude, in roughly [-1, 1].
    0.0 when fewer than 2 points or flat series.
    """
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, values))
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0.0:
        return 0.0
    slope = num / den
    scale = abs(my) if my != 0.0 else 1.0
    return max(-1.0, min(1.0, slope / scale))


def _asset_id(asset: Any) -> float:
    """Stable numeric id for an asset (hash % 64). LightGBM learns per-asset effects."""
    if not asset:
        return 0.0
    return float(abs(hash(str(asset))) % 64)


# ─────────────────────────────────────────────────────────────────────────────
#  OHLC GEOMETRY (the wave) — OFFLINE, no indicators
# ─────────────────────────────────────────────────────────────────────────────
def extract_geometry_from_candles(
    candles_m1: Any,
    candles_m5: Any,
    candles_m15: Any,
    direction: str,
) -> dict[str, float]:
    """Compute the 7 OHLC-geometry features from raw candle snapshots.

    Args:
        candles_m1/m5/m15: list[dict|dict-like] or JSON string. The window of
            bars immediately BEFORE the entry bar (M1 = most recent, M15 = HTF
            context). May be empty/None → all geometry features default to 0.
        direction: "CALL" or "PUT" (expected trade direction).

    Returns a dict with the 7 geometry keys (subset of FEATURE_NAMES).
    """
    dir_up = str(direction).upper() == "CALL"

    m1 = _parse_candles(candles_m1)
    m5 = _parse_candles(candles_m5)
    m15 = _parse_candles(candles_m15)

    # Entry bar = last M1 bar (the bar on which the trade would trigger).
    entry_bar = m1[-1] if m1 else None
    o, h, l, c = _candle_ohlc(entry_bar) if entry_bar else (0.0, 0.0, 0.0, 0.0)
    rng = (h - l) if (h - l) > 0 else 0.0

    # body_dir: +1 if close>=open (bullish body), -1 bearish. Aligned with CALL?
    if rng > 0 or (h > l):
        body_signed = 1.0 if c >= o else -1.0
    else:
        body_signed = 0.0
    body_dir = body_signed if dir_up else -body_signed

    # body_ratio: |close-open| / range  (0=doji, 1=full body)
    body_ratio = (abs(c - o) / rng) if rng > 0 else 0.0

    # opp_wick_ratio: opposing wick / range.
    #   CALL expects upward move → opposing wick is the LOWER wick.
    #   PUT expects downward move → opposing wick is the UPPER wick.
    if rng > 0:
        if dir_up:
            opp_wick = min(o, c) - l
        else:
            opp_wick = h - max(o, c)
        opp_wick_ratio = max(0.0, opp_wick) / rng
    else:
        opp_wick_ratio = 0.0

    # entry_extreme_pos: where the bar closed within its range, oriented to
    #   direction. 1.0 = closed at the directional extreme (entered at extreme,
    #   e.g. spike with conviction); 0.0 = closed at the opposite extreme.
    if rng > 0:
        if dir_up:
            entry_extreme_pos = (c - l) / rng
        else:
            entry_extreme_pos = (h - c) / rng
    else:
        entry_extreme_pos = 0.5

    # pre_trend_slope: slope of the M1 closes BEFORE the entry bar.
    pre = m1[:-1] if len(m1) > 1 else m1
    pre_closes = [_candle_ohlc(x)[3] for x in pre]
    pre_trend_slope = _linreg_slope(pre_closes)

    # compression_geom: ratio of the entry-bar range to the M15 recent range.
    #   Small entry bar inside a wide HTF range => compression (coil).
    m15_ranges = [(_candle_ohlc(x)[1] - _candle_ohlc(x)[2]) for x in m15 if _candle_ohlc(x)[1] > _candle_ohlc(x)[2]]
    if m15_ranges:
        avg_m15 = sum(m15_ranges) / len(m15_ranges)
    else:
        avg_m15 = rng
    if avg_m15 > 0:
        compression_geom = max(0.0, min(1.0, 1.0 - (rng / avg_m15)))
    else:
        compression_geom = 0.0

    # fractal_align: does the entry bar break the M15 prior fractal?
    #   1.0 if entry bar makes a new extreme vs the prior M15 bars in the
    #   expected direction, 0.0 otherwise, 0.5 neutral.
    fractal_align = 0.5
    if len(m15) >= 3:
        prior_highs = [_candle_ohlc(x)[1] for x in m15[:-1]]
        prior_lows = [_candle_ohlc(x)[2] for x in m15[:-1]]
        if dir_up and prior_highs and h > max(prior_highs):
            fractal_align = 1.0
        elif (not dir_up) and prior_lows and l < min(prior_lows):
            fractal_align = 1.0
        elif (dir_up and prior_highs and h < max(prior_highs)) or (
            (not dir_up) and prior_lows and l > min(prior_lows)
        ):
            fractal_align = 0.0

    return {
        "body_dir": round(body_dir, 4),
        "body_ratio": round(body_ratio, 4),
        "opp_wick_ratio": round(opp_wick_ratio, 4),
        "entry_extreme_pos": round(entry_extreme_pos, 4),
        "pre_trend_slope": round(pre_trend_slope, 4),
        "compression_geom": round(compression_geom, 4),
        "fractal_align": round(fractal_align, 4),
    }


def _parse_candles(raw: Any) -> list[Any]:
    """Normalize a candles field (JSON string or list) to a list."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, (list, tuple)):
        return [x for x in raw if x is not None]
    return []


def _parse_stoch_zone(raw: Any) -> float:
    """Extract the zone int from a stochastic JSON/dict (handles nested forms)."""
    if raw is None:
        return 0.0
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return 0.0
    if isinstance(raw, dict):
        if "zone" in raw:
            return _encode_zone(raw["zone"])
        # some rows store the zone as the raw value
        for k in ("k", "d", "estado", "zone_int"):
            if k in raw and isinstance(raw[k], (int, float)):
                return float(raw[k])
        return 0.0
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  LEGACY: extract_features(strategy_json) — keeps the old 18-key contract
# ─────────────────────────────────────────────────────────────────────────────
def extract_features(strategy_json: dict) -> dict[str, float]:
    """Extract ML features from a candidate's strategy_json dict.

    Retains the legacy derived/stochastic features. Geometry + extra-context
    features are filled with 0.0 (they require raw candles, see
    :func:`extract_features_full`). This keeps backward compatibility with
    DB rows that only carry a strategy_json.
    """
    ps = strategy_json.get("pattern_snapshot") or {}
    mq = ps.get("math_quality") or {}
    bd = ps.get("score_breakdown") or {}

    stoch: dict[str, Any] = strategy_json.get("stoch_m15") or {}

    feats: dict[str, float] = {
        # Math quality
        "math_hurst": float(mq.get("hurst", 0.5)),
        "math_r_squared": float(mq.get("r_squared", 0.0)),
        "math_angle_deg": float(mq.get("angle_deg", 0.0)),
        "math_squeeze": float(mq.get("squeeze", 0.0)),
        "math_composite": float(mq.get("composite", 50.0)),
        # Stochastic (legacy: only M15 wired here)
        "stoch_m15_zone": _encode_zone(stoch.get("zone")),
        "stoch_m5_zone": 0.0,
        "stoch_m1_zone": 0.0,
        # Wyckoff
        "spring_margin": float(strategy_json.get("spring_margin") or 0.0),
        # Score breakdown
        "score_compression": float(bd.get("compression", 0.0)),
        "score_bounce": float(bd.get("bounce", 0.0)),
        "score_fractal": float(bd.get("fractal", 0.0)),
        "score_context": float(bd.get("context", 0.0)),
        "score_payout": float(bd.get("payout", 0.0)),
        "score_stoch_help": float(bd.get("stoch_help", 0.0)),
        # Geometry (no candles here → 0)
        "body_dir": 0.0,
        "body_ratio": 0.0,
        "opp_wick_ratio": 0.0,
        "entry_extreme_pos": 0.0,
        "pre_trend_slope": 0.0,
        "compression_geom": 0.0,
        "fractal_align": 0.0,
        # Signal context
        "direction": 1.0 if strategy_json.get("direction") == "CALL" else 0.0,
        "payout": float(strategy_json.get("payout", 85)),
        "duration_sec": float(strategy_json.get("duration_sec", 300)),
        "hour_utc": 0.0,
        "dow": 0.0,
        "asset_id": 0.0,
    }
    return feats


# ─────────────────────────────────────────────────────────────────────────────
#  FULL: extract_features_full(row) — uses raw candles + all context
# ─────────────────────────────────────────────────────────────────────────────
def extract_features_full(row: dict) -> dict[str, float]:
    """Extract the COMPLETE feature vector from a scan_candidates DB row.

    Reads the raw candle snapshots (candles_1m/5m/15m), the stochastic across
    the 3 timeframes (stoch_m15/m5/m1), and the signal context (direction,
    payout, duration_sec, asset, timestamp) — all already stored in the row.
    Computes the OHLC geometry OFFLINE. This is what the training pipeline and
    the live scorer use.
    """
    # Strategy_json (if present) supplies the legacy math/score fields.
    sj_raw = row.get("strategy_json")
    if isinstance(sj_raw, str):
        try:
            sj = json.loads(sj_raw)
        except (json.JSONDecodeError, TypeError):
            sj = {}
    elif isinstance(sj_raw, dict):
        sj = sj_raw
    else:
        sj = {}

    feats = extract_features(sj)

    # Override with any explicitly stored legacy fields.
    if row.get("spring_margin") is not None:
        feats["spring_margin"] = float(row["spring_margin"])

    direction = str(row.get("direction") or sj.get("direction") or "CALL")
    feats["direction"] = 1.0 if direction.upper() == "CALL" else 0.0

    if row.get("payout") is not None:
        feats["payout"] = float(row["payout"])
    if row.get("duration_sec") is not None:
        feats["duration_sec"] = float(row["duration_sec"])
    feats["asset_id"] = _asset_id(row.get("asset") or sj.get("asset"))

    # Stochastic across 3 timeframes.
    feats["stoch_m15_zone"] = _parse_stoch_zone(row.get("stoch_m15"))
    feats["stoch_m5_zone"] = _parse_stoch_zone(row.get("stoch_m5"))
    feats["stoch_m1_zone"] = _parse_stoch_zone(row.get("stoch_m1"))

    # OHLC geometry from raw candles (OFFLINE).
    geom = extract_geometry_from_candles(
        row.get("candles_1m"),
        row.get("candles_5m"),
        row.get("candles_15m"),
        direction,
    )
    feats.update(geom)

    # Time context from timestamp (if present).
    ts = row.get("ts")
    hour_utc, dow = _time_context(ts)
    feats["hour_utc"] = hour_utc
    feats["dow"] = dow

    return feats


def _time_context(ts: Any) -> tuple[float, float]:
    """Return (hour_utc 0-23, dow 0-6) from an epoch/ISO timestamp, else (0,0)."""
    import datetime as _dt
    from datetime import timezone as _tz

    epoch = None
    if isinstance(ts, (int, float)):
        epoch = float(ts)
        if epoch > 1e12:  # ms
            epoch = epoch / 1000.0
    elif isinstance(ts, str):
        s = ts.strip()
        if not s:
            return 0.0, 0.0
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                epoch = _dt.datetime.strptime(s, fmt).replace(
                    tzinfo=_tz.utc
                ).timestamp()
                break
            except ValueError:
                continue
        if epoch is None:
            try:
                epoch = _dt.datetime.fromisoformat(
                    s.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                return 0.0, 0.0
    if epoch is None:
        return 0.0, 0.0
    dt = _dt.datetime.fromtimestamp(epoch, tz=_tz.utc)
    return float(dt.hour), float(dt.weekday())


# ─────────────────────────────────────────────────────────────────────────────
#  DB-row adapter (kept for callers that pass a row dict)
# ─────────────────────────────────────────────────────────────────────────────
def extract_from_db_row(row: dict) -> dict[str, float]:
    """Extract ML features from a DB row dict.

    Delegates to :func:`extract_features_full` (which handles candles,
    stochastic and context). Falls back gracefully when fields are missing.
    """
    return extract_features_full(row)


def validate_features(features: dict) -> bool:
    """Check that all FEATURE_NAMES keys are present and numeric."""
    for name in FEATURE_NAMES:
        if name not in features:
            return False
        val = features[name]
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return False
    return True
