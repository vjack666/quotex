"""Análisis estructural SMC: swings, FVG, BOS/CHoCH y zonas."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from models import Candle


class Bias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class StructureEventType(str, Enum):
    BOS_UP = "BOS_UP"
    BOS_DOWN = "BOS_DOWN"
    CHOCH_UP = "CHOCH_UP"
    CHOCH_DOWN = "CHOCH_DOWN"


@dataclass
class SwingPoint:
    index: int
    ts: int
    price: float
    is_high: bool


@dataclass
class StructureEvent:
    index: int
    ts: int
    event_type: StructureEventType
    broken_level: float
    label: str = ""


@dataclass
class FVG:
    index: int
    ts: int
    top: float
    bottom: float
    is_bullish: bool


@dataclass
class Zone:
    top: float
    bottom: float
    is_supply: bool
    origin_ts: int
    fvg_adjacent: bool = False
    score: float = 0.0


@dataclass
class StructureResult:
    bias: Bias
    swings: List[SwingPoint] = field(default_factory=list)
    events: List[StructureEvent] = field(default_factory=list)
    fvgs: List[FVG] = field(default_factory=list)
    zones: List[Zone] = field(default_factory=list)


def detect_swings(candles: Sequence[Candle], strength: int = 3) -> List[SwingPoint]:
    n = len(candles)
    swings: List[SwingPoint] = []

    for i in range(strength, n - strength):
        neighbours = range(i - strength, i + strength + 1)

        is_sh = all(
            candles[i].high >= candles[j].high
            for j in neighbours if j != i
        ) and candles[i].high > max(candles[j].high for j in neighbours if j != i)

        is_sl = all(
            candles[i].low <= candles[j].low
            for j in neighbours if j != i
        ) and candles[i].low < min(candles[j].low for j in neighbours if j != i)

        if is_sh:
            swings.append(SwingPoint(
                index=i, ts=candles[i].ts, price=candles[i].high, is_high=True,
            ))
        elif is_sl:
            swings.append(SwingPoint(
                index=i, ts=candles[i].ts, price=candles[i].low, is_high=False,
            ))

    return swings


def detect_fvg(
    candles: Sequence[Candle],
    min_size_pct: float = 0.0002,
) -> List[FVG]:
    fvgs: List[FVG] = []

    for i in range(2, len(candles)):
        prev2 = candles[i - 2]
        mid = candles[i - 1]
        curr = candles[i]
        ref = (mid.high + mid.low) / 2 or 1.0

        if curr.low > prev2.high:
            gap = curr.low - prev2.high
            if gap / ref >= min_size_pct:
                fvgs.append(FVG(
                    index=i - 1, ts=mid.ts,
                    top=curr.low, bottom=prev2.high,
                    is_bullish=True,
                ))
        elif curr.high < prev2.low:
            gap = prev2.low - curr.high
            if gap / ref >= min_size_pct:
                fvgs.append(FVG(
                    index=i - 1, ts=mid.ts,
                    top=prev2.low, bottom=curr.high,
                    is_bullish=False,
                ))

    return fvgs


def _label_structure_events(swings: List[SwingPoint]) -> List[StructureEvent]:
    events: List[StructureEvent] = []

    highs = [sw for sw in swings if sw.is_high]
    lows = [sw for sw in swings if not sw.is_high]

    if len(highs) < 2 or len(lows) < 2:
        return events

    current_bias = Bias.NEUTRAL
    all_sorted = sorted(swings, key=lambda s: s.index)
    prev_high = highs[0]
    prev_low = lows[0]

    for sw in all_sorted[1:]:
        if sw.is_high:
            if sw.price > prev_high.price:
                if current_bias == Bias.BULLISH:
                    events.append(StructureEvent(
                        index=sw.index, ts=sw.ts,
                        event_type=StructureEventType.BOS_UP,
                        broken_level=prev_high.price,
                        label=f"BOS ↑  rompió {prev_high.price:.5f}",
                    ))
                else:
                    events.append(StructureEvent(
                        index=sw.index, ts=sw.ts,
                        event_type=StructureEventType.CHOCH_UP,
                        broken_level=prev_high.price,
                        label="CHoCH ↑  RETROCESO HACIA ZONA DE VENTA",
                    ))
                    current_bias = Bias.BULLISH
            elif current_bias == Bias.BEARISH:
                events.append(StructureEvent(
                    index=sw.index, ts=sw.ts,
                    event_type=StructureEventType.BOS_DOWN,
                    broken_level=prev_high.price,
                    label=f"BOS ↓  LH confirmado {sw.price:.5f}",
                ))
            prev_high = sw
        else:
            if sw.price < prev_low.price:
                if current_bias == Bias.BEARISH:
                    events.append(StructureEvent(
                        index=sw.index, ts=sw.ts,
                        event_type=StructureEventType.BOS_DOWN,
                        broken_level=prev_low.price,
                        label=f"BOS ↓  rompió {prev_low.price:.5f}",
                    ))
                else:
                    events.append(StructureEvent(
                        index=sw.index, ts=sw.ts,
                        event_type=StructureEventType.CHOCH_DOWN,
                        broken_level=prev_low.price,
                        label="CHoCH ↓  RETROCESO HACIA ZONA DE COMPRA",
                    ))
                    current_bias = Bias.BEARISH
            elif current_bias == Bias.BULLISH:
                events.append(StructureEvent(
                    index=sw.index, ts=sw.ts,
                    event_type=StructureEventType.BOS_UP,
                    broken_level=prev_low.price,
                    label=f"BOS ↑  HL confirmado {sw.price:.5f}",
                ))
            prev_low = sw

    return events


def _compute_bias(events: List[StructureEvent], swings: List[SwingPoint]) -> Bias:
    if not events:
        if len(swings) < 4:
            return Bias.NEUTRAL
        mid = len(swings) // 2
        early = sum(sw.price for sw in swings[:mid]) / mid
        late = sum(sw.price for sw in swings[mid:]) / (len(swings) - mid)
        if late > early * 1.0003:
            return Bias.BULLISH
        if late < early * 0.9997:
            return Bias.BEARISH
        return Bias.NEUTRAL

    score = 0
    for ev in events[-6:]:
        if ev.event_type in (StructureEventType.BOS_UP, StructureEventType.CHOCH_UP):
            score += 1
        else:
            score -= 1

    if score > 0:
        return Bias.BULLISH
    if score < 0:
        return Bias.BEARISH
    return Bias.NEUTRAL


def _extract_zones(
    swings: List[SwingPoint],
    fvgs: List[FVG],
    candles: Sequence[Candle],
    fvg_window: int = 5,
) -> List[Zone]:
    zones: List[Zone] = []

    for sw in swings:
        candle = candles[sw.index]
        body = abs(candle.close - candle.open)
        buffer = max(body, sw.price * 0.0008)

        if sw.is_high:
            zone_top = sw.price
            zone_bottom = sw.price - buffer
            is_supply = True
            need_bullish_fvg = False
        else:
            zone_top = sw.price + buffer
            zone_bottom = sw.price
            is_supply = False
            need_bullish_fvg = True

        fvg_adjacent = any(
            abs(f.index - sw.index) <= fvg_window
            and f.is_bullish == need_bullish_fvg
            for f in fvgs
        )

        if not fvg_adjacent:
            continue

        zones.append(Zone(
            top=zone_top,
            bottom=zone_bottom,
            is_supply=is_supply,
            origin_ts=sw.ts,
            fvg_adjacent=True,
            score=1.0,
        ))

    return zones


def detect_structure(
    candles: Sequence[Candle],
    swing_strength: int = 3,
    min_fvg_pct: float = 0.0002,
) -> StructureResult:
    if len(candles) < 2 * swing_strength + 2:
        return StructureResult(bias=Bias.NEUTRAL)

    swings = detect_swings(candles, strength=swing_strength)
    fvgs = detect_fvg(candles, min_size_pct=min_fvg_pct)
    events = _label_structure_events(swings)
    bias = _compute_bias(events, swings)
    zones = _extract_zones(swings, fvgs, candles)

    return StructureResult(
        bias=bias,
        swings=swings,
        events=events,
        fvgs=fvgs,
        zones=zones,
    )