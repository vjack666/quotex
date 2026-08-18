from __future__ import annotations

from dataclasses import dataclass
import time
from typing import List

from core.models import Candle
from spike_filter import sanitize_spike_candles

REVERSAL_MIN_STRENGTH = 0.55


@dataclass
class CandleSignal:
    pattern_name: str
    strength: float
    confirms_direction: bool


# ── Clasificador de FORMA de vela (auditoría / caja negra) ────────────────
# Reutiliza los nombres de patrones existentes del proyecto (inglés):
#   doji, hammer, shooting_star, inverted_hammer, marubozu, spinning_top,
#   bullish_engulfing, bearish_engulfing, bullish, bearish, none.
# Devuelve la forma de la vela MÁS la estructura OHLC para auditoría.


def classify_candle_shape(candle: Candle, prev: "Candle | None" = None) -> dict:
    """Clasifica la FORMA de una vela con los nombres existentes del proyecto."""
    r = _total_range(candle)
    if r <= 0:
        return {"name": "none", "side": "doji", "body_pct": 0.0, "upper_wick_pct": 0.0, "lower_wick_pct": 0.0, "body": 0.0, "total_range": 0.0, "open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close, "ts": candle.ts}
    body = _body(candle)
    body_pct = body / r
    upper_pct = _upper_wick(candle) / r
    lower_pct = _lower_wick(candle) / r
    side = "bull" if _is_bullish(candle) else ("bear" if _is_bearish(candle) else "doji")
    name = "none"
    if prev is not None and _engulfs(candle, prev):
        name = "bullish_engulfing" if _is_bullish(candle) else "bearish_engulfing"
    elif body > 0 and _body_high_zone(candle) and _lower_wick(candle) >= (2.0 * body) and _upper_wick(candle) < (0.2 * r):
        name = "hammer"
    elif body > 0 and _body_low_zone(candle) and _upper_wick(candle) >= (2.0 * body) and _lower_wick(candle) < (0.2 * r):
        name = "shooting_star"
    elif body > 0 and _body_low_zone(candle) and _upper_wick(candle) >= (3.0 * body):
        name = "inverted_hammer"
    elif body_pct >= 0.8 and upper_pct < 0.1 and lower_pct < 0.1:
        name = "marubozu"
    elif body_pct <= 0.1 + 1e-9:
        name = "doji"
    elif body_pct < 0.35:
        name = "spinning_top"
    elif side == "bull":
        name = "bullish"
    elif side == "bear":
        name = "bearish"
    return {"name": name, "side": side, "body_pct": round(body_pct, 4), "upper_wick_pct": round(upper_pct, 4), "lower_wick_pct": round(lower_pct, 4), "body": round(body, 6), "total_range": round(r, 6), "open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close, "ts": candle.ts}


def last_closed_shape(candles: List[Candle]) -> dict:
    if not candles:
        return {"name": "none", "side": "doji", "ts": 0}
    prev = candles[-2] if len(candles) >= 2 else None
    target = candles[-2] if len(candles) >= 2 else candles[-1]
    return classify_candle_shape(target, prev=prev)


def _body(c: Candle) -> float: return abs(c.close - c.open)
def _upper_wick(c: Candle) -> float: return c.high - max(c.open, c.close)
def _lower_wick(c: Candle) -> float: return min(c.open, c.close) - c.low
def _total_range(c: Candle) -> float: return c.high - c.low

def _body_pct(c: Candle) -> float:
    r = _total_range(c)
    return 0.0 if r <= 0 else _body(c) / r

def _is_bullish(c: Candle) -> bool: return c.close > c.open
def _is_bearish(c: Candle) -> bool: return c.close < c.open

def _body_high_zone(c: Candle) -> bool:
    r = _total_range(c)
    return r > 0 and min(c.open, c.close) >= c.low + (0.55 * r)

def _body_low_zone(c: Candle) -> bool:
    r = _total_range(c)
    return r > 0 and max(c.open, c.close) <= c.low + (0.45 * r)

def _is_strong_bull(c: Candle) -> bool:
    r = _total_range(c)
    return r > 0 and _is_bullish(c) and (_body(c) / r) >= 0.5

def _is_strong_bear(c: Candle) -> bool:
    r = _total_range(c)
    return r > 0 and _is_bearish(c) and (_body(c) / r) >= 0.5

def _engulfs(curr: Candle, prev: Candle) -> bool:
    return min(curr.open, curr.close) <= min(prev.open, prev.close) and max(curr.open, curr.close) >= max(prev.open, prev.close)


def detect_reversal_pattern(candles_1m: List[Candle], direction: str) -> CandleSignal:
    if len(candles_1m) < 3: return CandleSignal("none", 0.0, False)
    curr, prev = candles_1m[-2], candles_1m[-3]
    body, total_range = _body(curr), _total_range(curr)
    if total_range <= 0: return CandleSignal("none", 0.0, False)
    upper_wick, lower_wick, body_pct = _upper_wick(curr), _lower_wick(curr), body / total_range
    if direction == "put":
        if _is_bearish(curr) and _is_bullish(prev) and _engulfs(curr, prev): return CandleSignal("bearish_engulfing", 0.85, True)
        if _is_bullish(prev) and body > 0 and _body_low_zone(curr) and upper_wick >= 2.0 * body and lower_wick < 0.2 * total_range: return CandleSignal("shooting_star", 0.75, True)
        if body_pct < 0.2 and _is_strong_bull(prev): return CandleSignal("evening_star_simple", 0.65, True)
        if body > 0 and _body_low_zone(curr) and upper_wick >= 3.0 * body: return CandleSignal("bearish_inverted_hammer", 0.55, True)
        if _is_bullish(curr) and _is_bearish(prev) and _engulfs(curr, prev): return CandleSignal("bullish_engulfing", 0.85, False)
        if _is_bearish(prev) and body > 0 and _body_high_zone(curr) and lower_wick >= 2.0 * body and upper_wick < 0.2 * total_range: return CandleSignal("hammer", 0.75, False)
        if body_pct < 0.2 and _is_strong_bear(prev): return CandleSignal("morning_star_simple", 0.65, False)
        if body > 0 and _body_high_zone(curr) and lower_wick >= 3.0 * body: return CandleSignal("bullish_hammer", 0.55, False)
        return CandleSignal("none", 0.0, False)
    if direction == "call":
        if _is_bullish(curr) and _is_bearish(prev) and _engulfs(curr, prev): return CandleSignal("bullish_engulfing", 0.85, True)
        if _is_bearish(prev) and body > 0 and _body_high_zone(curr) and lower_wick >= 2.0 * body and upper_wick < 0.2 * total_range: return CandleSignal("hammer", 0.75, True)
        if body_pct < 0.2 and _is_strong_bear(prev): return CandleSignal("morning_star_simple", 0.65, True)
        if body > 0 and _body_high_zone(curr) and lower_wick >= 3.0 * body: return CandleSignal("bullish_hammer", 0.55, True)
        if _is_bearish(curr) and _is_bullish(prev) and _engulfs(curr, prev): return CandleSignal("bearish_engulfing", 0.85, False)
        if _is_bullish(prev) and body > 0 and _body_low_zone(curr) and upper_wick >= 2.0 * body and lower_wick < 0.2 * total_range: return CandleSignal("shooting_star", 0.75, False)
        if body_pct < 0.2 and _is_strong_bull(prev): return CandleSignal("evening_star_simple", 0.65, False)
        if body > 0 and _body_low_zone(curr) and upper_wick >= 3.0 * body: return CandleSignal("bearish_inverted_hammer", 0.55, False)
        return CandleSignal("none", 0.0, False)
    return CandleSignal("none", 0.0, False)


def explain_no_pattern_reason(candles_1m: List[Candle], direction: str) -> str:
    if len(candles_1m) < 3: return f"insuficientes velas 1m ({len(candles_1m)}/3)"
    curr, prev = candles_1m[-2], candles_1m[-3]
    total_range = _total_range(curr)
    if total_range <= 0: return "vela 1m cerrada sin rango (high==low)"
    if direction not in {"put", "call"}: return f"dirección inválida '{direction}'"
    body, upper_wick, lower_wick = _body(curr), _upper_wick(curr), _lower_wick(curr)
    body_pct = body / total_range
    prev_side = "bull" if _is_bullish(prev) else ("bear" if _is_bearish(prev) else "doji")
    curr_side = "bull" if _is_bullish(curr) else ("bear" if _is_bearish(curr) else "doji")
    expected = "bearish_engulfing|shooting_star|evening_star_simple|bearish_inverted_hammer" if direction == "put" else "bullish_engulfing|hammer|morning_star_simple|bullish_hammer"
    return f"sin match [{expected}] prev={prev_side} curr={curr_side} body_pct={body_pct:.2f} up/body={(upper_wick / max(body, 1e-9)):.2f} down/body={(lower_wick / max(body, 1e-9)):.2f}"


async def fetch_candles_1m(client, asset: str, count: int = 10) -> List[Candle]:
    end_time, tf_sec, offset = time.time(), 60, count * 60
    try: raw_list = await client.get_candles(asset, end_time, offset, tf_sec)
    except Exception: return []
    if not raw_list: return []
    candles: List[Candle] = []
    for raw in raw_list:
        if not isinstance(raw, dict): continue
        try: candle = Candle(ts=int(raw["time"]), open=float(raw["open"]), high=float(raw["high"]), low=float(raw["low"]), close=float(raw["close"]))
        except (KeyError, TypeError, ValueError): continue
        if candle.high > 0: candles.append(candle)
    ordered = sorted(candles, key=lambda c: c.ts)
    filtered, _stats = sanitize_spike_candles(ordered)
    return filtered
