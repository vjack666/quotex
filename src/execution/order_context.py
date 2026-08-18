"""Behavior-neutral order context used by execution extraction."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderContext:
    asset: str
    direction: str
    amount: float
    duration_sec: int
    stage: str = "normal"
    payout: int | None = None
    score: float | None = None
    signal_ts: float | int | None = None
    strategy_origin: str | None = None

__all__ = ["OrderContext"]
