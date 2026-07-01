"""Estructuras de datos compartidas entre módulos."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List

from config import DURATION_SEC, MIN_PAYOUT


@dataclass
class Candle:
    ts: int
    open: float
    high: float
    low: float
    close: float

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low


@dataclass
class ConsolidationZone:
    asset: str
    ceiling: float
    floor: float
    bars_inside: int
    detected_at: float
    range_pct: float

    @property
    def midpoint(self) -> float:
        return (self.ceiling + self.floor) / 2

    @property
    def age_minutes(self) -> float:
        return (time.time() - self.detected_at) / 60


class SignalMode(Enum):
    REBOUND = "rebound"
    BREAKOUT = "breakout"


@dataclass
class CandidateEntry:
    asset: str
    payout: int
    zone: ConsolidationZone
    direction: str
    candles: List[Candle]
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    reversal_pattern: str = "none"
    reversal_strength: float = 0.0
    reversal_confirms: bool = False
    mode: SignalMode = SignalMode.REBOUND
    candles_h1: List[Candle] = field(default_factory=list)
    zone_memory: list = field(default_factory=list)

    def __str__(self) -> str:
        bd = self.score_breakdown
        mode_label = self.mode.value
        return (
            f"{self.asset:20s} {self.direction.upper():4s} [{mode_label}] "
            f"SCORE={self.score:.1f}/100 "
            f"[compression={bd.get('compression', 0):.1f} "
            f"bounce/momentum={bd.get('bounce', bd.get('momentum', 0)):.1f} "
            f"trend={bd.get('trend', 0):.1f} "
            f"payout={bd.get('payout', 0):.1f}]"
        )


@dataclass
class TradeState:
    asset: str
    direction: str
    amount: float
    entry_price: float
    ceiling: float
    floor: float
    order_id: str = ""
    order_ref: int = 0
    opened_at: float = field(default_factory=time.time)
    martin_fired: bool = False
    stage: str = "initial"
    journal_id: int = 0
    strategy_origin: str = "STRAT-A"
    duration_sec: int = DURATION_SEC
    payout: int = MIN_PAYOUT
    resolved: bool = False
    score_original: float = 0.0


@dataclass
class EntryTimingInfo:
    ok: bool
    lag_sec: float
    duration_sec: int
    time_since_open_sec: float
    secs_to_close_sec: float
    decision: str


@dataclass
class PendingReversal:
    asset: str
    zone: ConsolidationZone
    proposed_direction: str
    conflicting_pattern: str
    detected_at: datetime
    entry_mode: str
    payout: int
    max_wait_scans: int = 3
    scans_waited: int = 0


@dataclass
class MartinPending:
    asset: str
    amount: float
    original_loss: float
    created_at: datetime
    score_original: float = 0.0
    max_wait_scans: int = 2
    scans_waited: int = 0


@dataclass
class OrderBlock:
    side: str
    low: float
    high: float
    created_ts: int
    created_index: int
    bars_ago: int = 0
    is_mitigated: bool = False


@dataclass
class MAState:
    ma35: float
    ma50: float
    trend: str
    cross: str
    avg_body: float = 0.0