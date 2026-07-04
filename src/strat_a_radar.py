"""STRAT-A hunter radar: watchlist de zonas casi listas (coarse → fine)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from config import (
    MIN_PAYOUT,
    STRAT_A_RADAR_MAX_WATCH,
    STRAT_A_RADAR_MIN_AGE_RATIO,
    STRAT_A_RADAR_MIN_READINESS,
    TOUCH_TOLERANCE_PCT,
    ZONE_AGE_BREAKOUT_MIN,
    ZONE_AGE_REBOUND_MIN,
)
from models import ConsolidationZone
from strat_a import price_at_ceiling, price_at_floor


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


@dataclass
class RadarWatchEntry:
    asset: str
    payout: int
    zone: ConsolidationZone
    direction: str
    entry_mode: str
    stage: str
    readiness_score: float
    side_label: str
    updated_at: float = field(default_factory=time.time)


def _side_label(entry_mode: str) -> str:
    if entry_mode == "rebound_ceiling":
        return "techo"
    if entry_mode == "rebound_floor":
        return "piso"
    if entry_mode.startswith("breakout"):
        return "ruptura"
    return "zona"


def _price_at_extreme(
    price: float,
    zone: ConsolidationZone,
    entry_mode: str,
    dynamic_touch_tolerance: float,
) -> bool:
    if entry_mode == "rebound_ceiling":
        return price_at_ceiling(price, zone.ceiling, dynamic_touch_tolerance)
    if entry_mode == "rebound_floor":
        return price_at_floor(price, zone.floor, dynamic_touch_tolerance)
    if entry_mode == "breakout_above":
        return price >= zone.ceiling * (1 - dynamic_touch_tolerance)
    if entry_mode == "breakout_below":
        return price <= zone.floor * (1 + dynamic_touch_tolerance)
    return False


def _age_ratio_ok(
    zone: ConsolidationZone,
    stage: str,
    min_age_ratio: float = STRAT_A_RADAR_MIN_AGE_RATIO,
) -> bool:
    if stage == "breakout":
        return zone.age_minutes >= ZONE_AGE_BREAKOUT_MIN
    min_age = ZONE_AGE_REBOUND_MIN * min_age_ratio
    return zone.age_minutes >= min_age


def should_watch(
    zone: ConsolidationZone,
    price: float,
    entry_mode: str,
    stage: str,
    dynamic_touch_tolerance: float,
    *,
    min_age_ratio: float = STRAT_A_RADAR_MIN_AGE_RATIO,
) -> bool:
    """Precio en extremo/ruptura y zona madura suficiente para vigilancia."""
    if entry_mode == "none":
        return False
    if not _price_at_extreme(price, zone, entry_mode, dynamic_touch_tolerance):
        return False
    return _age_ratio_ok(zone, stage, min_age_ratio)


def compute_readiness(
    zone: ConsolidationZone,
    price: float,
    payout: int,
    entry_mode: str,
    stage: str,
    *,
    ev_score: float = 0.0,
    in_pending: bool = False,
    dynamic_touch_tolerance: float = TOUCH_TOLERANCE_PCT,
) -> float:
    """Puntuación 0–100: proximidad al extremo, madurez, compresión, payout."""
    if entry_mode == "rebound_ceiling":
        ref = zone.ceiling
        dist = abs(price - ref) / ref if ref else 1.0
    elif entry_mode == "rebound_floor":
        ref = zone.floor
        dist = abs(price - ref) / ref if ref else 1.0
    elif entry_mode.startswith("breakout"):
        dist = 0.0
        ref = zone.ceiling if entry_mode == "breakout_above" else zone.floor
    else:
        return 0.0

    tol = max(dynamic_touch_tolerance, 1e-12)
    proximity = 30.0 * _clamp(1.0 - dist / tol, 0.0, 1.0)

    min_age = ZONE_AGE_BREAKOUT_MIN if stage == "breakout" else ZONE_AGE_REBOUND_MIN
    age_ratio = zone.age_minutes / min_age if min_age > 0 else 0.0
    maturity = min(30.0, age_ratio * 30.0)

    compression = min(15.0, max(0.0, (0.005 - zone.range_pct) / 0.005 * 15.0))
    payout_pts = min(15.0, (payout / 95.0) * 15.0) if payout >= MIN_PAYOUT else 0.0
    pending_bonus = 10.0 if in_pending else 0.0
    ev_bonus = min(10.0, max(0.0, ev_score * 0.1))

    return _clamp(proximity + maturity + compression + payout_pts + pending_bonus + ev_bonus, 0.0, 100.0)


def rank_and_trim(
    entries: list[RadarWatchEntry],
    max_watch: int = STRAT_A_RADAR_MAX_WATCH,
    min_readiness: float = STRAT_A_RADAR_MIN_READINESS,
) -> list[RadarWatchEntry]:
    """Ordena por readiness y conserva solo top-N por encima del umbral."""
    qualified = [e for e in entries if e.readiness_score >= min_readiness]
    qualified.sort(key=lambda e: (-e.readiness_score, e.asset))
    return qualified[:max_watch]