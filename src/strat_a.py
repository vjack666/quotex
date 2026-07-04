"""Estrategia A: consolidación en 5m (señal pura, sin I/O)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from statistics import mean
from typing import List, Optional

from candle_patterns import CandleSignal, detect_reversal_pattern
from config import (
    ATR_PERIOD,
    FORCE_EXECUTE_STRONG_BREAKOUT,
    H1_CONFIRM_ENABLED,
    H1_EMA_FAST,
    H1_EMA_SLOW,
    MAX_RANGE_PCT,
    MIN_CONSOLIDATION_BARS,
    ORDER_BLOCK_LOOKBACK,
    ORDER_BLOCK_MAX_PER_SIDE,
    ORDER_BLOCK_TOUCH_TOLERANCE_PCT,
    PATTERN_PUT_BLACKLIST,
    REBOUND_MIN_STRENGTH_CALL,
    REBOUND_MIN_STRENGTH_PUT,
    REJECTION_CANDLE_MIN_BODY,
    REJECTION_PUT_MIN_UPPER_WICK,
    STRICT_PATTERN_CHECK,
    STRAT_A_ZONE_MIN_AGE_REBOUND,
    TOUCH_TOLERANCE_PCT,
    VOLUME_LOOKBACK,
    VOLUME_MULTIPLIER,
    ZONE_AGE_BREAKOUT_MIN,
    ZONE_AGE_REBOUND_MIN,
)
from models import Candle, ConsolidationZone, MAState, OrderBlock


@dataclass
class PendingReversalHint:
    """Pista para que scanner encole espera activa; sin mutación en strat_a."""
    proposed_direction: str
    entry_mode: str
    conflicting_pattern: str
    update_existing: bool = True


@dataclass
class ScoreAdjustments:
    reversal_bonus: float = 0.0
    reversal_penalty: float = 0.0
    weak_confirmation: float = 0.0
    breakout_bonus: float = 0.0
    order_block: float = 0.0
    ma_filter: float = 0.0


@dataclass
class StratAEvaluation:
    has_signal: bool
    direction: str | None = None
    entry_mode: str = "none"
    stage: str = "initial"
    zone: ConsolidationZone | None = None
    pattern_name: str = "none"
    strength: float = 0.0
    confirms: bool = False
    rejection_ok: bool = False
    skip_reason: str | None = None
    breakout_strength_ok: bool = False
    skip_zone_age_check: bool = False
    pending_reversal_hint: PendingReversalHint | None = None
    score_adjustments: ScoreAdjustments = field(default_factory=ScoreAdjustments)
    ob_info: str = ""
    ma_info: str = ""
    force_execute: bool = False


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [mean(values[:period])]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def avg_body(candles: List[Candle], n: int = VOLUME_LOOKBACK) -> float:
    recent = candles[-(n + 1):-1] if len(candles) > n else candles[:-1]
    if not recent:
        return 0.0
    return mean(c.body for c in recent) or 0.0


def is_high_volume_break(candle: Candle, candles_history: List[Candle]) -> bool:
    avg = avg_body(candles_history)
    if avg == 0:
        return True
    return candle.body >= avg * VOLUME_MULTIPLIER


def compute_atr(candles: List[Candle], period: int = ATR_PERIOD) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs: List[float] = []
    for i in range(1, len(candles)):
        c = candles[i]
        prev = candles[i - 1]
        tr = max(
            c.high - c.low,
            abs(c.high - prev.close),
            abs(c.low - prev.close),
        )
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    return mean(trs[-period:])


def infer_h1_trend(candles_h1: List[Candle]) -> str:
    if len(candles_h1) < H1_EMA_SLOW + 5:
        return "neutral"
    closes = [c.close for c in candles_h1]
    ef = _ema(closes, H1_EMA_FAST)
    es = _ema(closes, H1_EMA_SLOW)
    if not ef or not es:
        return "neutral"
    ef_last = ef[-1]
    es_last = es[-1]
    price = closes[-1]
    if ef_last > es_last and price >= ef_last:
        return "bullish"
    if ef_last < es_last and price <= ef_last:
        return "bearish"
    return "neutral"


def detect_consolidation(
    candles: List[Candle],
    max_range_pct: float = MAX_RANGE_PCT,
) -> Optional[ConsolidationZone]:
    needed = MIN_CONSOLIDATION_BARS + 2
    if len(candles) < needed:
        return None

    for end in range(len(candles), MIN_CONSOLIDATION_BARS - 1, -1):
        start = end - MIN_CONSOLIDATION_BARS
        window = candles[start:end]

        ceiling = max(c.high for c in window)
        floor = min(c.low for c in window)
        mid = (ceiling + floor) / 2
        if mid == 0:
            continue

        range_pct = (ceiling - floor) / mid
        if range_pct > max_range_pct:
            continue

        bars_inside = sum(1 for c in window if floor <= c.close <= ceiling)
        if bars_inside < MIN_CONSOLIDATION_BARS:
            continue

        touches_ceiling = sum(
            1 for c in window if c.high >= ceiling * (1 - TOUCH_TOLERANCE_PCT)
        )
        touches_floor = sum(
            1 for c in window if c.low <= floor * (1 + TOUCH_TOLERANCE_PCT)
        )
        if (touches_ceiling + touches_floor) < 2:
            continue

        return ConsolidationZone(
            asset="",
            ceiling=ceiling,
            floor=floor,
            bars_inside=bars_inside,
            detected_at=time.time(),
            range_pct=range_pct,
        )

    return None


def price_at_ceiling(
    price: float,
    ceiling: float,
    tolerance_pct: float = TOUCH_TOLERANCE_PCT,
) -> bool:
    return abs(price - ceiling) / ceiling <= tolerance_pct


def price_at_floor(
    price: float,
    floor: float,
    tolerance_pct: float = TOUCH_TOLERANCE_PCT,
) -> bool:
    return abs(price - floor) / floor <= tolerance_pct


def broke_above(candle: Candle, ceiling: float) -> bool:
    return candle.close > ceiling * (1 + TOUCH_TOLERANCE_PCT)


def broke_below(candle: Candle, floor: float) -> bool:
    return candle.close < floor * (1 - TOUCH_TOLERANCE_PCT)


def required_rebound_strength(direction: str) -> float:
    return REBOUND_MIN_STRENGTH_PUT if direction == "put" else REBOUND_MIN_STRENGTH_CALL


def is_put_pattern_blacklisted(direction: str, pattern_name: str) -> bool:
    return direction == "put" and pattern_name in PATTERN_PUT_BLACKLIST


def validate_rejection_candle(
    candles_1m: List[Candle],
    direction: str,
    min_body_ratio: float = REJECTION_CANDLE_MIN_BODY,
) -> tuple[bool, str]:
    if len(candles_1m) < 3:
        return False, "insuficientes velas 1m"

    last = candles_1m[-2]
    rango = last.range
    if rango <= 0:
        return False, "vela sin rango"

    body_ratio = abs(last.close - last.open) / rango

    if direction == "call":
        if last.close <= last.open:
            return False, f"vela bajista (close={last.close:.5f} < open={last.open:.5f})"
        if body_ratio < min_body_ratio:
            return False, f"cuerpo débil {body_ratio:.0%} < {min_body_ratio:.0%}"
        return True, ""

    if direction == "put":
        if last.close >= last.open:
            return False, f"vela alcista (close={last.close:.5f} >= open={last.open:.5f})"
        if body_ratio < min_body_ratio:
            return False, f"cuerpo débil {body_ratio:.0%} < {min_body_ratio:.0%}"
        upper_wick = last.high - max(last.open, last.close)
        upper_wick_ratio = upper_wick / rango
        if upper_wick_ratio < REJECTION_PUT_MIN_UPPER_WICK:
            return False, (
                f"mecha superior débil {upper_wick_ratio:.0%} "
                f"< {REJECTION_PUT_MIN_UPPER_WICK:.0%}"
            )
        return True, ""

    return False, "dirección inválida"


def detect_order_blocks(candles: List[Candle]) -> dict[str, list[OrderBlock]]:
    if len(candles) < 6:
        return {"bull": [], "bear": []}

    result: dict[str, list[OrderBlock]] = {"bull": [], "bear": []}
    total = len(candles)
    lookback_window = min(30, total)
    bodies = [float(c.body) for c in candles[-lookback_window:]]
    avg_body_val = mean(bodies) if bodies else 0.0

    if avg_body_val < 1e-12:
        return result

    impulse_threshold = avg_body_val * 1.5
    start_idx = max(1, total - ORDER_BLOCK_LOOKBACK)

    for j in range(start_idx + 1, total):
        c_impulse = candles[j]

        if c_impulse.close < c_impulse.open and c_impulse.body >= impulse_threshold:
            for k in range(j - 1, max(j - 4, start_idx - 1), -1):
                if candles[k].close > candles[k].open:
                    result["bear"].append(
                        OrderBlock(
                            side="bear",
                            low=float(candles[k].low),
                            high=float(candles[k].high),
                            created_ts=int(candles[k].ts),
                            created_index=k,
                            bars_ago=(total - 1 - k),
                        )
                    )
                    break

        if c_impulse.close > c_impulse.open and c_impulse.body >= impulse_threshold:
            for k in range(j - 1, max(j - 4, start_idx - 1), -1):
                if candles[k].close < candles[k].open:
                    result["bull"].append(
                        OrderBlock(
                            side="bull",
                            low=float(candles[k].low),
                            high=float(candles[k].high),
                            created_ts=int(candles[k].ts),
                            created_index=k,
                            bars_ago=(total - 1 - k),
                        )
                    )
                    break

    def _deduplicate(blocks: list[OrderBlock]) -> list[OrderBlock]:
        seen: set[tuple[int, str]] = set()
        dedup: list[OrderBlock] = []
        for b in blocks:
            key = (b.created_index, b.side)
            if key not in seen:
                seen.add(key)
                dedup.append(b)
        return dedup

    result["bull"] = _deduplicate(result["bull"])
    result["bear"] = _deduplicate(result["bear"])

    def _is_invalidated(block: OrderBlock) -> bool:
        future_closes = [float(c.close) for c in candles[block.created_index + 1:]]
        if not future_closes:
            return False
        if block.side == "bear":
            return any(cl > block.high for cl in future_closes)
        return any(cl < block.low for cl in future_closes)

    def _check_mitigation(block: OrderBlock) -> bool:
        for c in candles[block.created_index + 1:]:
            if float(c.high) >= block.low and float(c.low) <= block.high:
                return True
        return False

    active_bull: list[OrderBlock] = []
    active_bear: list[OrderBlock] = []
    for b in result["bull"]:
        if not _is_invalidated(b):
            b.is_mitigated = _check_mitigation(b)
            active_bull.append(b)
    for b in result["bear"]:
        if not _is_invalidated(b):
            b.is_mitigated = _check_mitigation(b)
            active_bear.append(b)

    active_bull.sort(key=lambda b: b.created_ts, reverse=True)
    active_bear.sort(key=lambda b: b.created_ts, reverse=True)
    return {
        "bull": active_bull[:ORDER_BLOCK_MAX_PER_SIDE],
        "bear": active_bear[:ORDER_BLOCK_MAX_PER_SIDE],
    }


def _block_distance(price: float, block: OrderBlock) -> float:
    if block.low <= price <= block.high:
        return 0.0
    return min(abs(price - block.low), abs(price - block.high))


def score_order_blocks(
    *,
    direction: str,
    price: float,
    blocks: dict[str, list[OrderBlock]],
    avg_body_val: float = 1e-9,
) -> tuple[float, str]:
    bull_blocks = blocks.get("bull", [])
    bear_blocks = blocks.get("bear", [])
    all_blocks = bull_blocks + bear_blocks

    if not all_blocks:
        return 0.0, "sin bloques activos"

    points = 0.0
    notes: list[str] = []
    price_in_bull = any(b.low <= price <= b.high for b in bull_blocks)
    price_in_bear = any(b.low <= price <= b.high for b in bear_blocks)
    proximity_threshold = max(avg_body_val, 1e-9)

    if direction == "call":
        if bear_blocks:
            nearest_bear = min(bear_blocks, key=lambda b: _block_distance(price, b))
            if price_in_bear:
                if nearest_bear.is_mitigated:
                    points -= 12.0
                    notes.append("-12 CALL en BEAR OB (mitigado)")
                else:
                    points -= 15.0
                    notes.append("-15 CALL en BEAR OB (sin mitigar)")
            else:
                dist = _block_distance(price, nearest_bear)
                if 0 < dist <= proximity_threshold:
                    points -= 8.0
                    notes.append(f"-8 CALL aproximándose a BEAR OB (dist={dist:.6f})")
        if bull_blocks:
            if price_in_bull:
                points += 8.0
                notes.append("+8 CALL en BULL OB (soporte retrace)")
            else:
                points += 3.0
                notes.append("+3 CALL alineado con BULL OB (fuera de zona)")

    if direction == "put":
        if bull_blocks:
            nearest_bull = min(bull_blocks, key=lambda b: _block_distance(price, b))
            if price_in_bull:
                if nearest_bull.is_mitigated:
                    points -= 12.0
                    notes.append("-12 PUT en BULL OB (mitigado)")
                else:
                    points -= 15.0
                    notes.append("-15 PUT en BULL OB (sin mitigar)")
            else:
                dist = _block_distance(price, nearest_bull)
                if 0 < dist <= proximity_threshold:
                    points -= 8.0
                    notes.append(f"-8 PUT aproximándose a BULL OB (dist={dist:.6f})")
        if bear_blocks:
            if price_in_bear:
                points += 8.0
                notes.append("+8 PUT en BEAR OB (resistencia retrace)")
            else:
                points += 3.0
                notes.append("+3 PUT alineado con BEAR OB (fuera de zona)")

    nearest = min(all_blocks, key=lambda b: _block_distance(price, b))
    mitigation_str = "mitigado" if nearest.is_mitigated else "sin mitigar"
    info = f"{nearest.side.upper()} @ {nearest.low:.5f}–{nearest.high:.5f} | {mitigation_str}"
    if notes:
        info = f"{', '.join(notes)} | {info}"
    return points, info


def compute_ma_state(
    candles_5m: List[Candle],
    prev_state: MAState | None = None,
) -> MAState | None:
    from config import MA_FAST_PERIOD, MA_LOOKBACK_CANDLES, MA_FLAT_DELTA_PCT, MA_SLOW_PERIOD

    if len(candles_5m) < MA_SLOW_PERIOD:
        return None

    closes = [float(c.close) for c in candles_5m[-MA_LOOKBACK_CANDLES:]]
    ma35 = mean(closes[-MA_FAST_PERIOD:])
    ma50 = mean(closes[-MA_SLOW_PERIOD:])
    price = closes[-1]
    delta_abs = abs(ma35 - ma50)
    flat_threshold = max(1e-9, price * MA_FLAT_DELTA_PCT)

    if delta_abs < flat_threshold:
        trend = "FLAT"
    elif ma35 > ma50:
        trend = "UP"
    else:
        trend = "DOWN"

    cross = "NONE"
    if prev_state is not None:
        if prev_state.ma35 <= prev_state.ma50 and ma35 > ma50:
            cross = "GOLDEN"
        elif prev_state.ma35 >= prev_state.ma50 and ma35 < ma50:
            cross = "DEATH"

    lookback_window = min(30, len(candles_5m))
    bodies = [float(c.body) for c in candles_5m[-lookback_window:]]
    avg_body_val = mean(bodies) if bodies else 0.0

    return MAState(
        ma35=float(ma35),
        ma50=float(ma50),
        trend=trend,
        cross=cross,
        avg_body=float(avg_body_val),
    )


def score_ma(direction: str, ma_state: MAState | None) -> tuple[float, str]:
    if ma_state is None:
        return 0.0, "sin datos"

    points = 0.0
    if direction == "call":
        if ma_state.trend == "UP":
            points += 6.0
        elif ma_state.trend == "DOWN":
            points -= 10.0
        if ma_state.cross == "GOLDEN":
            points += 4.0
    else:
        if ma_state.trend == "DOWN":
            points += 6.0
        elif ma_state.trend == "UP":
            points -= 10.0
        if ma_state.cross == "DEATH":
            points += 4.0

    info = (
        f"trend={ma_state.trend} cross={ma_state.cross} "
        f"ma35={ma_state.ma35:.5f} ma50={ma_state.ma50:.5f}"
    )
    return points, info


def compute_dynamic_range(candles: List[Candle]) -> tuple[float, float, float]:
    """Retorna (dynamic_max_range, atr_pct, dynamic_touch_tolerance)."""
    from config import (
        ATR_RANGE_FACTOR,
        MAX_DYNAMIC_RANGE_PCT,
        MAX_RANGE_PCT,
        MIN_DYNAMIC_RANGE_PCT,
        TOUCH_TOLERANCE_PCT,
        USE_DYNAMIC_ATR_RANGE,
    )

    dynamic_max_range = MAX_RANGE_PCT
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
        dynamic_touch_tolerance = _clamp(atr_pct * 0.12, 0.00015, 0.00080)
    return dynamic_max_range, atr_pct, dynamic_touch_tolerance


def _resolve_entry_direction(
    last: Candle,
    candles_5m: List[Candle],
    zone: ConsolidationZone,
    price: float,
    dynamic_touch_tolerance: float,
) -> tuple[str | None, str, str, bool]:
    """Retorna (direction, entry_mode, stage, breakout_strength_ok)."""
    if price_at_ceiling(price, zone.ceiling, dynamic_touch_tolerance):
        return "put", "rebound_ceiling", "initial", False
    if price_at_floor(price, zone.floor, dynamic_touch_tolerance):
        return "call", "rebound_floor", "initial", False
    if broke_above(last, zone.ceiling) and is_high_volume_break(last, candles_5m):
        return "call", "breakout_above", "breakout", True
    if broke_below(last, zone.floor) and is_high_volume_break(last, candles_5m):
        return "put", "breakout_below", "breakout", True
    return None, "none", "initial", False


def _compute_score_adjustments(
    *,
    direction: str,
    price: float,
    blocks: dict[str, list[OrderBlock]],
    ma_state: MAState | None,
    pattern_name: str,
    strength: float,
    confirms: bool,
    stage: str,
    breakout_strength_ok: bool,
) -> tuple[ScoreAdjustments, str, str]:
    adjustments = ScoreAdjustments()
    if confirms and strength >= 0.60:
        adjustments.reversal_bonus = 8.0
    elif confirms and strength >= REBOUND_MIN_STRENGTH_CALL:
        adjustments.reversal_bonus = 5.0
    elif (not confirms) and pattern_name != "none":
        adjustments.reversal_penalty = -15.0
    elif pattern_name == "none":
        adjustments.weak_confirmation = -10.0

    if stage == "breakout" and breakout_strength_ok:
        adjustments.breakout_bonus = 6.0

    ob_points, ob_info = score_order_blocks(
        direction=direction,
        price=price,
        blocks=blocks,
        avg_body_val=ma_state.avg_body if ma_state else 1e-9,
    )
    if ob_points != 0:
        adjustments.order_block = round(ob_points, 1)

    ma_points, ma_info = score_ma(direction, ma_state)
    if ma_points != 0:
        adjustments.ma_filter = round(ma_points, 1)

    return adjustments, ob_info, ma_info


def evaluate_strat_a(
    *,
    candles_5m: list[Candle],
    candles_1m: list[Candle],
    zone: ConsolidationZone,
    blocks: dict[str, list[OrderBlock]],
    ma_state: MAState | None,
    price: float | None = None,
    dynamic_touch_tolerance: float | None = None,
    h1_trend: str = "neutral",
    h1_confirm_enabled: bool = H1_CONFIRM_ENABLED,
    strict_pattern_check: bool = STRICT_PATTERN_CHECK,
    force_execute_strong_breakout: bool = FORCE_EXECUTE_STRONG_BREAKOUT,
    zone_age_rebound_min: int = STRAT_A_ZONE_MIN_AGE_REBOUND,
    zone_age_breakout_min: int = ZONE_AGE_BREAKOUT_MIN,
    pattern_signal: CandleSignal | None = None,
) -> StratAEvaluation:
    """Evalúa señal STRAT-A sin I/O."""
    if price is None:
        price = candles_5m[-1].close
    if dynamic_touch_tolerance is None:
        _, _, dynamic_touch_tolerance = compute_dynamic_range(candles_5m)

    last = candles_5m[-1]
    direction, entry_mode, stage, breakout_strength_ok = _resolve_entry_direction(
        last,
        candles_5m,
        zone,
        price,
        dynamic_touch_tolerance,
    )

    if direction is None:
        return StratAEvaluation(
            has_signal=False,
            entry_mode="none",
            zone=zone,
            skip_reason="no_direction",
        )

    skip_zone_age_check = stage == "breakout" and breakout_strength_ok
    min_zone_age = zone_age_breakout_min if stage == "breakout" else zone_age_rebound_min
    if (not skip_zone_age_check) and zone.age_minutes < min_zone_age:
        return StratAEvaluation(
            has_signal=False,
            direction=direction,
            entry_mode=entry_mode,
            stage=stage,
            zone=zone,
            breakout_strength_ok=breakout_strength_ok,
            skip_zone_age_check=skip_zone_age_check,
            skip_reason="zone_too_young",
        )

    pattern_name = "none"
    strength = 0.0
    confirms = False
    if pattern_signal is not None:
        pattern_name = pattern_signal.pattern_name
        strength = pattern_signal.strength
        confirms = pattern_signal.confirms_direction
    elif len(candles_1m) >= 3:
        signal_1m = detect_reversal_pattern(candles_1m, direction)
        pattern_name = signal_1m.pattern_name
        strength = signal_1m.strength
        confirms = signal_1m.confirms_direction

    rejection_ok = False
    if entry_mode.startswith("rebound"):
        candle_valid, candle_fail_reason = validate_rejection_candle(
            candles_1m,
            direction,
            REJECTION_CANDLE_MIN_BODY,
        )
        if not candle_valid:
            return StratAEvaluation(
                has_signal=False,
                direction=direction,
                entry_mode=entry_mode,
                stage=stage,
                zone=zone,
                pattern_name=pattern_name,
                strength=strength,
                confirms=confirms,
                rejection_ok=False,
                breakout_strength_ok=breakout_strength_ok,
                skip_zone_age_check=skip_zone_age_check,
                skip_reason="rejection_candle_fail",
                pending_reversal_hint=PendingReversalHint(
                    proposed_direction=direction,
                    entry_mode=entry_mode,
                    conflicting_pattern=candle_fail_reason,
                ),
            )

        rejection_ok = True
        if pattern_name == "none":
            hint = PendingReversalHint(
                proposed_direction=direction,
                entry_mode=entry_mode,
                conflicting_pattern="none",
                update_existing=direction != "put",
            )
            return StratAEvaluation(
                has_signal=False,
                direction=direction,
                entry_mode=entry_mode,
                stage=stage,
                zone=zone,
                pattern_name=pattern_name,
                strength=strength,
                confirms=confirms,
                rejection_ok=True,
                breakout_strength_ok=breakout_strength_ok,
                skip_zone_age_check=skip_zone_age_check,
                skip_reason="pattern_missing",
                pending_reversal_hint=hint,
            )

        req_strength = required_rebound_strength(direction)
        if is_put_pattern_blacklisted(direction, pattern_name):
            return StratAEvaluation(
                has_signal=False,
                direction=direction,
                entry_mode=entry_mode,
                stage=stage,
                zone=zone,
                pattern_name=pattern_name,
                strength=strength,
                confirms=confirms,
                rejection_ok=True,
                breakout_strength_ok=breakout_strength_ok,
                skip_zone_age_check=skip_zone_age_check,
                skip_reason="put_pattern_blacklisted",
                pending_reversal_hint=PendingReversalHint(
                    proposed_direction=direction,
                    entry_mode=entry_mode,
                    conflicting_pattern=pattern_name,
                ),
            )

        pattern_ok = confirms and strength >= req_strength
        if not pattern_ok:
            if (
                strict_pattern_check
                and pattern_name != "none"
                and (not confirms)
                and strength >= 0.65
            ):
                return StratAEvaluation(
                    has_signal=False,
                    direction=direction,
                    entry_mode=entry_mode,
                    stage=stage,
                    zone=zone,
                    pattern_name=pattern_name,
                    strength=strength,
                    confirms=confirms,
                    rejection_ok=True,
                    breakout_strength_ok=breakout_strength_ok,
                    skip_zone_age_check=skip_zone_age_check,
                    skip_reason="strict_pattern_veto",
                )
            if direction == "put":
                conflict = (
                    f"{pattern_name}:{strength:.2f}"
                    if pattern_name != "none"
                    else pattern_name
                )
                return StratAEvaluation(
                    has_signal=False,
                    direction=direction,
                    entry_mode=entry_mode,
                    stage=stage,
                    zone=zone,
                    pattern_name=pattern_name,
                    strength=strength,
                    confirms=confirms,
                    rejection_ok=True,
                    breakout_strength_ok=breakout_strength_ok,
                    skip_zone_age_check=skip_zone_age_check,
                    skip_reason="pattern_insufficient",
                    pending_reversal_hint=PendingReversalHint(
                        proposed_direction=direction,
                        entry_mode=entry_mode,
                        conflicting_pattern=conflict,
                        update_existing=False,
                    ),
                )
            if pattern_name != "none" and not confirms:
                return StratAEvaluation(
                    has_signal=False,
                    direction=direction,
                    entry_mode=entry_mode,
                    stage=stage,
                    zone=zone,
                    pattern_name=pattern_name,
                    strength=strength,
                    confirms=confirms,
                    rejection_ok=True,
                    breakout_strength_ok=breakout_strength_ok,
                    skip_zone_age_check=skip_zone_age_check,
                    skip_reason="pattern_insufficient",
                    pending_reversal_hint=PendingReversalHint(
                        proposed_direction=direction,
                        entry_mode=entry_mode,
                        conflicting_pattern=pattern_name,
                    ),
                )
            return StratAEvaluation(
                has_signal=False,
                direction=direction,
                entry_mode=entry_mode,
                stage=stage,
                zone=zone,
                pattern_name=pattern_name,
                strength=strength,
                confirms=confirms,
                rejection_ok=True,
                breakout_strength_ok=breakout_strength_ok,
                skip_zone_age_check=skip_zone_age_check,
                skip_reason="pattern_insufficient",
            )

    if h1_confirm_enabled:
        if (direction == "put" and h1_trend == "bullish") or (
            direction == "call" and h1_trend == "bearish"
        ):
            return StratAEvaluation(
                has_signal=False,
                direction=direction,
                entry_mode=entry_mode,
                stage=stage,
                zone=zone,
                pattern_name=pattern_name,
                strength=strength,
                confirms=confirms,
                rejection_ok=rejection_ok,
                breakout_strength_ok=breakout_strength_ok,
                skip_zone_age_check=skip_zone_age_check,
                skip_reason="h1_conflict",
            )

    score_adj, ob_info, ma_info = _compute_score_adjustments(
        direction=direction,
        price=price,
        blocks=blocks,
        ma_state=ma_state,
        pattern_name=pattern_name,
        strength=strength,
        confirms=confirms,
        stage=stage,
        breakout_strength_ok=breakout_strength_ok,
    )
    force_execute = bool(
        force_execute_strong_breakout and stage == "breakout" and breakout_strength_ok
    )

    return StratAEvaluation(
        has_signal=True,
        direction=direction,
        entry_mode=entry_mode,
        stage=stage,
        zone=zone,
        pattern_name=pattern_name,
        strength=strength,
        confirms=confirms,
        rejection_ok=rejection_ok,
        breakout_strength_ok=breakout_strength_ok,
        skip_zone_age_check=skip_zone_age_check,
        score_adjustments=score_adj,
        ob_info=ob_info,
        ma_info=ma_info,
        force_execute=force_execute,
    )