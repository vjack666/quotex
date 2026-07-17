"""M1 micro-trend confirmation gate (pure, no I/O).

Blocks buy only when the last closed M1 candle is clearly against the
intended direction. Fail-open on insufficient data so data collection
is not starved by missing candles.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def confirm_m1_micro(
    candles_1m: Sequence[Any] | None,
    direction: str,
) -> tuple[bool, str, dict]:
    """Confirm that M1 micro-trend is not clearly against ``direction``.

    Returns ``(ok, reason, metrics)``.

    Block rules (only when clearly against):
    - CALL blocked if last close < last open AND last close < prev close
    - PUT blocked if last close > last open AND last close > prev close

    Insufficient candles / unreadable OHLC → fail-open
    (``ok=True``, reason ``m1_insufficient_pass``).
    """
    metrics: dict = {
        "last_close": None,
        "last_open": None,
        "prev_close": None,
        "direction": (direction or "").strip().upper(),
        "candle_count": 0,
    }

    if not candles_1m or len(candles_1m) < 2:
        metrics["candle_count"] = 0 if not candles_1m else len(candles_1m)
        return True, "m1_insufficient_pass", metrics

    last = candles_1m[-1]
    prev = candles_1m[-2]
    try:
        last_open = float(_field(last, "open"))
        last_close = float(_field(last, "close"))
        prev_close = float(_field(prev, "close"))
    except (TypeError, ValueError, KeyError, AttributeError):
        metrics["candle_count"] = len(candles_1m)
        return True, "m1_insufficient_pass", metrics

    metrics.update(
        {
            "last_close": last_close,
            "last_open": last_open,
            "prev_close": prev_close,
            "candle_count": len(candles_1m),
        }
    )

    direction_u = (direction or "").strip().upper()
    if direction_u not in ("CALL", "PUT"):
        return True, "m1_ok", metrics

    if direction_u == "CALL":
        against = last_close < last_open and last_close < prev_close
        if against:
            return False, "m1_against_call", metrics
        return True, "m1_ok", metrics

    # PUT
    against = last_close > last_open and last_close > prev_close
    if against:
        return False, "m1_against_put", metrics
    return True, "m1_ok", metrics


def _field(candle: Any, name: str) -> Any:
    """Read OHLC from object attribute or mapping key."""
    if isinstance(candle, Mapping):
        return candle[name]
    return getattr(candle, name)
