"""Multi-timeframe confluence scoring for STRAT-F signals."""
from __future__ import annotations

import numpy as np
from typing import Optional


def detect_trend(candles: list, threshold: float = 0.001) -> str:
    """Detect trend using linear regression slope on closes.

    Returns 'CALL', 'PUT', or 'NEUTRAL'.
    Uses last 10 closes max, needs >= 3 candles.
    Normalizes slope by average price.
    """
    if len(candles) < 3:
        return "NEUTRAL"

    closes = np.array([c.close for c in candles[-10:]], dtype=np.float64)
    n = len(closes)
    x = np.arange(n, dtype=np.float64)

    slope, _ = np.polyfit(x, closes, 1)

    avg_price = float(np.mean(closes))
    if avg_price == 0:
        return "NEUTRAL"

    normalized_slope = slope / avg_price

    if normalized_slope > threshold:
        return "CALL"
    elif normalized_slope < -threshold:
        return "PUT"
    else:
        return "NEUTRAL"


def calculate_confluence(
    trends: dict[str, str], h1_available: bool = True
) -> tuple[str, float]:
    """Calculate confluence bonus from multi-TF trends.

    With H1 (4 TFs): 4/4 aligned -> +0.15, 3/4 -> +0.05, else -> -0.05
    Without H1 (3 TFs): 3/3 -> +0.10, 2/3 -> +0.03, else -> -0.03
    Returns (label, bonus).
    """
    if h1_available:
        tf_keys = ["M1", "M5", "M15", "H1"]
    else:
        tf_keys = ["M1", "M5", "M15"]

    active_trends = [trends.get(k, "NEUTRAL") for k in tf_keys]
    active_trends = [t for t in active_trends if t != "NEUTRAL"]

    if not active_trends:
        return ("NO_ALIGN", -0.05 if h1_available else -0.03)

    call_count = sum(1 for t in active_trends if t == "CALL")
    put_count = sum(1 for t in active_trends if t == "PUT")
    total_active = len(active_trends)
    dominant = "CALL" if call_count >= put_count else "PUT"
    aligned = max(call_count, put_count)

    if h1_available:
        if aligned >= 4:
            return (f"{dominant} 4/4", 0.15)
        elif aligned == 3:
            return (f"{dominant} 3/4", 0.05)
        else:
            return (f"MIXED {total_active}/{len(tf_keys)}", -0.05)
    else:
        if aligned >= 3:
            return (f"{dominant} 3/3", 0.10)
        elif aligned == 2:
            return (f"{dominant} 2/3", 0.03)
        else:
            return (f"MIXED {total_active}/{len(tf_keys)}", -0.03)


def compute_confluence_bonus(
    candles_1m: list,
    candles_5m: list,
    candles_15m: list,
    candles_1h: Optional[list] = None,
    threshold: float = 0.001,
) -> tuple[str, float, dict]:
    """Main entry point. Returns (label, bonus, trend_details).

    trend_details = {"M1": "CALL", "M5": "PUT", "M15": "NEUTRAL", "H1": "CALL"}
    """
    trend_details: dict[str, str] = {
        "M1": detect_trend(candles_1m, threshold),
        "M5": detect_trend(candles_5m, threshold),
        "M15": detect_trend(candles_15m, threshold),
    }

    h1_available = candles_1h is not None
    if h1_available:
        trend_details["H1"] = detect_trend(candles_1h, threshold)

    label, bonus = calculate_confluence(trend_details, h1_available)

    return (label, bonus, trend_details)
