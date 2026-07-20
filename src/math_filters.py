"""Mathematical and trigonometric signal quality filters.

Replaces blunt volatility measures (ATR) with geometric analysis that lets
the system SEE the shape of the market — not just how much it moves, but
HOW it moves.

All functions are pure (no I/O). Input: list of Candle objects. Output: float/dict.
"""
from __future__ import annotations
from typing import List, Sequence
from models import Candle


def fractal_dimension(closes: Sequence[float]) -> float:
    """Compute fractal dimension via box-counting (Hurst-like).
    
    Returns a value in [0, 1]:
    - H > 0.55 → trending market (momentum strategies work)
    - H ≈ 0.5  → random walk
    - H < 0.45 → mean-reverting (rebound strategies work — STRAT-F lives here)
    
    Uses the rescaled range (R/S) method simplified for candle data.
    The key insight: fractal dimension D = 2 - H, where H is the Hurst exponent.
    We compute H via the exponent of R/S vs window size.
    """
    if len(closes) < 10:
        return 0.5  # insufficient data → neutral
    
    n = len(closes)
    max_k = min(n // 2, 20)  # window sizes from 4 to max_k
    rs_values = []
    ns = []
    
    for k in range(4, max_k + 1):
        rs_sum = 0.0
        count = 0
        # Use non-overlapping windows
        for start in range(0, n - k + 1, k):
            window = list(closes[start:start + k])
            if len(window) < k:
                continue
            mean_w = sum(window) / len(window)
            deviations = [v - mean_w for v in window]
            cumulative = []
            s = 0.0
            for d in deviations:
                s += d
                cumulative.append(s)
            R = max(cumulative) - min(cumulative)
            # Standard deviation
            var = sum(d * d for d in deviations) / len(deviations)
            S = var ** 0.5 if var > 0 else 1e-10
            rs_sum += R / S
            count += 1
        
        if count > 0:
            rs_values.append(rs_sum / count)
            ns.append(float(k))
    
    if len(rs_values) < 3:
        return 0.5
    
    # Linear regression on log(R/S) vs log(n) to get Hurst exponent
    # H = slope of log(R/S) = f(log(n))
    log_ns = [_safe_log(x) for x in ns]
    log_rs = [_safe_log(x) for x in rs_values]
    slope = _linear_slope(log_ns, log_rs)
    
    # Clamp to [0.1, 0.9] — values outside are noise
    return max(0.1, min(0.9, slope))


def _safe_log(x: float) -> float:
    import math
    if x <= 0:
        return 0.0
    return math.log(x)


def _linear_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope of y = mx + b."""
    n = len(xs)
    if n < 2:
        return 0.5
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-15:
        return 0.5
    return (n * sum_xy - sum_x * sum_y) / denom


def trend_r_squared(candles: Sequence[Candle], period: int = 20) -> float:
    """R² of linear regression on close prices — measures trend "cleanliness".
    
    Returns [0, 1]:
    - R² > 0.8 → strong clean trend (momentum works)
    - R² 0.4-0.8 → moderate trend
    - R² < 0.4 → choppy/random (rebound strategies better)
    
    This is NOT a direction indicator — it measures HOW LINEAR the move is.
    A steep but choppy move has low R². A gentle but smooth move has high R².
    """
    if len(candles) < period:
        period = len(candles)
    if period < 5:
        return 0.0
    
    window = candles[-period:]
    closes = [float(c.close) for c in window]
    n = len(closes)
    xs = list(range(n))
    
    mean_x = sum(xs) / n
    mean_y = sum(closes) / n
    
    ss_tot = 0.0
    ss_res = 0.0
    
    # Compute slope and intercept
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, closes))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if abs(den) > 1e-15 else 0.0
    intercept = mean_y - slope * mean_x
    
    for x, y in zip(xs, closes):
        predicted = slope * x + intercept
        ss_res += (y - predicted) ** 2
        ss_tot += (y - mean_y) ** 2
    
    if ss_tot < 1e-15:
        return 0.0
    return max(0.0, min(1.0, 1.0 - ss_res / ss_tot))


def price_vector_angle(candles: Sequence[Candle], period: int = 10) -> float:
    """Geometric angle of the price vector (in degrees from horizontal).
    
    Uses atan2(dy, dx) where:
    - dy = price change (close[-1] - close[-period])
    - dx = number of candles (horizontal distance)
    
    Returns angle in degrees:
    - ~0° → flat/horizontal (consolidation)
    - > 15° → noticeable upward move
    - < -15° → noticeable downward move
    - |angle| > 30° → strong trend
    
    The angle is NORMALIZED by the average candle range so it's comparable
    across different price levels (BTC vs EURUSD).
    """
    if len(candles) < period:
        period = len(candles)
    if period < 2:
        return 0.0
    
    window = candles[-period:]
    dy = float(window[-1].close) - float(window[0].close)
    dx = float(period)  # horizontal distance in candles
    
    # Normalize dy by average candle range to make it dimensionless
    avg_range = sum(float(c.high - c.low) for c in window) / len(window)
    if avg_range < 1e-15:
        return 0.0
    
    normalized_dy = dy / avg_range
    
    import math
    angle_rad = math.atan2(normalized_dy, dx)
    return math.degrees(angle_rad)


def bollinger_squeeze(candles: Sequence[Candle], period: int = 20, num_std: float = 2.0) -> float:
    """Bollinger Band width normalized — detects compression ("the spring").
    
    Returns [0, 1]:
    - < 0.2 → tight squeeze (expect expansion — potential Wyckoff spring)
    - 0.2-0.5 → normal range
    - > 0.5 → expanded (trending, high volatility)
    
    For STRAT-F: a squeeze followed by a fractal = higher probability setup.
    The squeeze means the market was coiled and the fractal marks the release.
    """
    if len(candles) < period:
        period = len(candles)
    if period < 5:
        return 0.5
    
    window = closes = [float(c.close) for c in candles[-period:]]
    n = len(closes)
    mean = sum(closes) / n
    var = sum((c - mean) ** 2 for c in closes) / n
    std = var ** 0.5
    
    if mean < 1e-15:
        return 0.5
    
    # Normalized bandwidth: (upper - lower) / middle
    bandwidth = (2 * num_std * std) / mean
    
    # Map to [0, 1] using empirical thresholds
    # 0.001 = very tight squeeze, 0.01 = normal, 0.03+ = expanded
    if bandwidth <= 0.001:
        return 0.0
    if bandwidth >= 0.03:
        return 1.0
    return (bandwidth - 0.001) / (0.03 - 0.001)


def compute_signal_quality(candles_5m: Sequence[Candle], direction: str) -> dict:
    """Combined math/trig signal quality assessment.
    
    Returns a dict with all metrics + a composite score [0, 100].
    
    For STRAT-F specifically:
    - Low fractal dimension (mean-reverting) = GOOD for rebound
    - Low R² (choppy) = GOOD for rebound (price oscillates)
    - Moderate angle (< 15°) = GOOD (consolidation, not runaway trend)
    - Squeeze = GOOD (spring about to release)
    """
    closes = [float(c.close) for c in candles_5m] if candles_5m else []
    
    h = fractal_dimension(closes) if closes else 0.5
    r2 = trend_r_squared(candles_5m) if candles_5m else 0.0
    angle = price_vector_angle(candles_5m) if candles_5m else 0.0
    squeeze = bollinger_squeeze(candles_5m) if candles_5m else 0.5
    
    # ── Composite score for STRAT-F rebound ──
    # Mean-reverting market (H < 0.5) is better for rebounds
    hurst_score = max(0.0, (0.5 - h) / 0.4) * 25.0  # 0-25 pts
    
    # Low R² = choppy = good for rebounds (price bounces)
    r2_score = max(0.0, (0.6 - r2) / 0.6) * 25.0  # 0-25 pts
    
    # Moderate angle (not too steep) = consolidation
    abs_angle = abs(angle)
    if abs_angle < 5:
        angle_score = 25.0  # flat = ideal for rebound
    elif abs_angle < 15:
        angle_score = 15.0  # slight trend = OK
    elif abs_angle < 25:
        angle_score = 5.0   # moderate trend = risky
    else:
        angle_score = 0.0   # strong trend = don't rebound
    
    # Squeeze = potential energy building
    squeeze_score = (1.0 - squeeze) * 25.0  # lower squeeze = higher score
    
    composite = hurst_score + r2_score + angle_score + squeeze_score
    
    return {
        "hurst": round(h, 3),
        "r_squared": round(r2, 3),
        "angle_deg": round(angle, 2),
        "squeeze": round(squeeze, 3),
        "composite": round(composite, 1),
        "hurst_score": round(hurst_score, 1),
        "r2_score": round(r2_score, 1),
        "angle_score": round(angle_score, 1),
        "squeeze_score": round(squeeze_score, 1),
    }


def compute_contextual_modifier(
    candles_5m: Sequence[Candle],
    direction: str,
    m15_context: str,
) -> dict:
    """Contextual strength modifier based on geometric signal quality.

    Combines 3 layers of intelligence:
    1. Proportional zones: composite maps to a strength delta (no dead zone —
       every composite value has an effect, just scaled).
    2. Contextual M15 weight: math filters weigh MORE when M15 is ambiguous
       (trend/broken) and LESS when M15 is clear (range).
    3. Consensus bonus: if 3+ of 4 filters agree on "favorable", extra +0.05.

    Returns dict with:
    - delta: float to add to strength (range approximately [-0.18, +0.15])
    - composite: raw composite score [0, 100]
    - zone: "boost" | "neutral" | "penalize_mild" | "penalize_strong"
    - m15_weight: float 0.0-1.0 (how much the math filters matter)
    - consensus_count: int (how many filters agree on favorable)
    - consensus_bonus: float (extra bonus if 3+ agree)
    """
    mq = compute_signal_quality(candles_5m, direction)
    composite = mq["composite"]

    # ── Layer 1: Proportional zone mapping ──
    # No dead zone — every composite value produces an effect.
    # Above 50: linear boost from 0 to +0.10
    # Below 50: linear penalty from 0 to -0.12
    if composite >= 50.0:
        zone_delta = (composite - 50.0) / 500.0  # 50→0, 100→+0.10
        zone_label = "boost" if composite > 65 else "neutral"
    else:
        zone_delta = -(50.0 - composite) / 420.0  # 50→0, 0→-0.12
        zone_label = "penalize_strong" if composite < 25 else "penalize_mild"

    # ── Layer 2: Contextual M15 weight ──
    # In range: math filters are a secondary signal (30% weight).
    # In trend: math filters are critical for avoiding counter-trend (70%).
    # Broken: math filters are the last line of defense (100%).
    # Unknown: neutral 50%.
    _ctx = (m15_context or "").lower()
    if _ctx == "range":
        m15_weight = 0.30
    elif _ctx in ("uptrend", "downtrend"):
        m15_weight = 0.70
    elif _ctx == "broken":
        m15_weight = 1.0
    else:
        m15_weight = 0.50

    weighted_delta = zone_delta * m15_weight

    # ── Layer 3: Consensus bonus ──
    # Count how many of the 4 filters favor the rebound direction.
    # "Favorable" = the filter value matches what a rebound strategy wants.
    consensus_count = 0
    # Hurst < 0.5 = mean-reverting = good for rebound
    if mq["hurst"] < 0.50:
        consensus_count += 1
    # R² < 0.5 = choppy = good for rebound
    if mq["r_squared"] < 0.50:
        consensus_count += 1
    # Angle < 10° = flat = good for rebound
    if abs(mq["angle_deg"]) < 10.0:
        consensus_count += 1
    # Squeeze < 0.4 = compressed = good for spring/rebound
    if mq["squeeze"] < 0.40:
        consensus_count += 1

    consensus_bonus = 0.0
    if consensus_count >= 3:
        consensus_bonus = 0.05  # 3 out of 4 agree → bonus
    if consensus_count >= 4:
        consensus_bonus = 0.08  # unanimous → bigger bonus

    total_delta = max(-0.18, min(0.15, weighted_delta + consensus_bonus))

    return {
        "delta": round(total_delta, 4),
        "composite": round(composite, 1),
        "zone": zone_label,
        "m15_weight": round(m15_weight, 2),
        "consensus_count": consensus_count,
        "consensus_bonus": round(consensus_bonus, 4),
        "hurst": mq["hurst"],
        "r_squared": mq["r_squared"],
        "angle_deg": mq["angle_deg"],
        "squeeze": mq["squeeze"],
    }
