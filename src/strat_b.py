"""Estrategia B: Spring / Upthrust (Wyckoff) en 1m."""
from __future__ import annotations

from statistics import mean
from typing import Any, Optional, Tuple

import pandas as pd

from config import STRAT_B_ALLOW_WYCKOFF_EARLY, STRAT_B_MIN_CONFIDENCE
from models import Candle
from strategy_spring_sweep import detect_spring_or_upthrust


def candles_to_dataframe(candles: list[Candle]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
        }
    )


def evaluate_strat_b(
    candles_1m: list[Candle],
    min_confidence: float = STRAT_B_MIN_CONFIDENCE,
    *,
    allow_early: bool = STRAT_B_ALLOW_WYCKOFF_EARLY,
) -> dict[str, Any] | None:
    if len(candles_1m) < 20:
        return None

    spring_df = candles_to_dataframe(candles_1m)
    signal, info = detect_spring_or_upthrust(spring_df, allow_early=allow_early)
    conf = float(info.get("confidence", 0.0) or 0.0)
    if not signal and conf < min_confidence:
        return None

    return {
        "signal": bool(signal),
        "confidence": conf,
        "reason": str(info.get("reason", "")),
        "signal_type": info.get("signal_type"),
        "direction": str(info.get("direction") or "call"),
        "info": info,
    }


def find_strong_support_2m(
    candles: list[Candle],
    lookback: int = 90,
) -> Tuple[Optional[float], int]:
    if len(candles) < 7:
        return None, 0

    sample = candles[-lookback:] if len(candles) > lookback else candles[:]
    avg_price = mean([c.close for c in sample]) if sample else 0.0
    if avg_price <= 0:
        return None, 0

    tol = max(avg_price * 0.0006, 1e-6)
    pivots: list[float] = []
    for i in range(2, len(sample) - 2):
        low = sample[i].low
        if (
            low <= sample[i - 1].low
            and low <= sample[i + 1].low
            and low <= sample[i - 2].low
            and low <= sample[i + 2].low
        ):
            pivots.append(low)

    if not pivots:
        return None, 0

    clusters: list[dict[str, Any]] = []
    for p in pivots:
        matched = False
        for c in clusters:
            if abs(p - c["center"]) <= tol:
                c["values"].append(p)
                c["center"] = mean(c["values"])
                matched = True
                break
        if not matched:
            clusters.append({"center": p, "values": [p]})

    best_price: Optional[float] = None
    best_touches = 0
    for c in clusters:
        center = float(c["center"])
        touches = sum(1 for bar in sample if abs(bar.low - center) <= tol)
        if touches > best_touches:
            best_touches = touches
            best_price = center

    if best_price is None:
        return None, 0
    return round(best_price, 5), int(best_touches)