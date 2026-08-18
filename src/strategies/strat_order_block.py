"""Estrategia Order Block 1m: detección de OBs y entry por revisita al rango."""
from __future__ import annotations

from statistics import mean
from typing import Optional

from core.models import Candle, OrderBlock

OB_AVG_BODY_LOOKBACK = 14
OB_MIN_BODY_RATIO = 1.5


def detect_order_block_entry(candles_1m: list[Candle], blocks: list[OrderBlock] | None = None, tolerance: float = 0.05) -> Optional[tuple[str, float, float, float]]:
    """Detecta entrada por Order Block en velas 1m."""
    if len(candles_1m) < 6:
        return None
    from strategies.strat_a import detect_order_blocks
    if blocks is None:
        blocks_dict = detect_order_blocks(candles_1m)
        all_blocks: list[OrderBlock] = blocks_dict.get("bull", []) + blocks_dict.get("bear", [])
    else:
        all_blocks = list(blocks)
    if not all_blocks:
        return None
    for ob in all_blocks:
        if ob.is_mitigated or _is_mitigated_design(ob, candles_1m):
            continue
        if not _price_revisits(ob, candles_1m, tolerance):
            continue
        strength = _calc_strength(ob, candles_1m)
        direction = "call" if ob.side == "bull" else "put"
        return (direction, round(strength, 4), ob.low, ob.high)
    return None


def _is_mitigated_design(ob: OrderBlock, candles: list[Candle]) -> bool:
    for c in candles:
        if c.ts <= ob.created_ts:
            continue
        if ob.side == "bull" and c.close < ob.low:
            return True
        if ob.side == "bear" and c.close > ob.high:
            return True
    return False


def _price_revisits(ob: OrderBlock, candles: list[Candle], tolerance: float) -> bool:
    ob_range = ob.high - ob.low
    tol_abs = ob_range * tolerance
    lower = ob.low - tol_abs
    upper = ob.high + tol_abs
    for c in candles:
        if c.ts <= ob.created_ts:
            continue
        if c.high >= lower and c.low <= upper:
            return True
    return False


def _calc_strength(ob: OrderBlock, candles: list[Candle]) -> float:
    if len(candles) < 5:
        return 0.5
    idx = ob.created_index
    if idx < 0 or idx >= len(candles):
        return 0.5
    lookback = candles[-OB_AVG_BODY_LOOKBACK:] if len(candles) >= OB_AVG_BODY_LOOKBACK else candles
    avg_body = mean(c.body for c in lookback) or 1e-12
    impulse_candle = None
    for j in range(idx + 1, min(idx + 5, len(candles))):
        c = candles[j]
        ratio = c.body / avg_body
        if ratio >= OB_MIN_BODY_RATIO:
            if ob.side == "bull" and c.close > c.open:
                impulse_candle = c
                break
            if ob.side == "bear" and c.close < c.open:
                impulse_candle = c
                break
    body_ratio = impulse_candle.body / avg_body if impulse_candle is not None else candles[idx].body / avg_body
    strength = min(1.0, (body_ratio - OB_MIN_BODY_RATIO) / 1.0)
    return max(0.0, strength)
