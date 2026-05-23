from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class StrategyName(str, Enum):
    STRAT_B = "STRAT-B"
    BOB = "BOB"


class SignalPhase(str, Enum):
    SETUP = "SETUP"
    RETEST = "RETEST"
    CONFIRMED = "CONFIRMED"


@dataclass
class StrategySignal:
    strategy: StrategyName
    symbol: str
    timeframe: str
    direction: str  # "call" | "put"
    phase: SignalPhase
    confidence: float
    payout: int
    reason: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutedSignal:
    signal: StrategySignal
    priority_score: float
    route_reason: str


@dataclass
class RouterSnapshot:
    generated_at: datetime
    total_signals: int
    routed_signals: int
    strat_b: int
    bob: int
    setup: int
    retest: int
    confirmed: int
    top_symbol: Optional[str] = None
    top_strategy: Optional[str] = None
    top_phase: Optional[str] = None
    top_confidence: float = 0.0


__all__ = [
    "RoutedSignal",
    "RouterSnapshot",
    "SignalPhase",
    "StrategyName",
    "StrategySignal",
]
