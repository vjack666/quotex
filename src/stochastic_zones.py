"""M15 stoch zone help over STRAT-F (pure, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Zone = Literal["Z1", "Z2", "Z3", "Z4", "Z5"]
Action = Literal["BOOST", "PASS", "VETO"]
StochHelpMode = Literal["off", "soft", "hard"]

_VALID_MODES = frozenset({"off", "soft", "hard"})


@dataclass(frozen=True)
class StochHelpResult:
    zone: Optional[Zone]
    action: Action
    score_delta: int
    reason: str  # stoch_boost | stoch_pass | stoch_extreme_against | stoch_no_k


def zone_from_k(k: Optional[float]) -> Optional[Zone]:
    """Map %K to Z1..Z5; None if k is None. Clamp to [0, 100]."""
    if k is None:
        return None
    clamped = max(0.0, min(100.0, float(k)))
    if clamped <= 20.0:
        return "Z1"
    if clamped <= 40.0:
        return "Z2"
    if clamped <= 60.0:
        return "Z3"
    if clamped < 80.0:
        return "Z4"
    return "Z5"


def apply_stoch_help(
    k: Optional[float],
    direction: str,
    mode: str,
) -> StochHelpResult:
    """Return zone/action/score_delta for STRAT-F direction.

    - mode "off": always PASS, score_delta 0 (zone still resolved if k present)
    - mode "soft": boosts only; never VETO
    - mode "hard": boosts + VETO on CALL+Z5 and PUT+Z1
    - k is None: PASS, score_delta 0, zone None
    - direction normalized case-insensitively to CALL/PUT
    - unknown mode: behave as "off" (fail-safe: no veto)
    """
    zone = zone_from_k(k)
    raw_mode = (mode or "").strip().lower()
    effective_mode: str = raw_mode if raw_mode in _VALID_MODES else "off"

    if k is None or zone is None:
        return StochHelpResult(zone=None, action="PASS", score_delta=0, reason="stoch_no_k")

    if effective_mode == "off":
        return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")

    direction_u = (direction or "").strip().upper()
    if direction_u not in ("CALL", "PUT"):
        return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")

    # Matrix locked by R3/R4
    if direction_u == "CALL":
        if zone == "Z1":
            return StochHelpResult(zone=zone, action="BOOST", score_delta=10, reason="stoch_boost")
        if zone == "Z2":
            return StochHelpResult(zone=zone, action="BOOST", score_delta=5, reason="stoch_boost")
        if zone in ("Z3", "Z4"):
            return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
        # Z5: VETO hard, PASS soft
        if effective_mode == "hard":
            return StochHelpResult(
                zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against"
            )
        return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")

    # PUT
    if zone == "Z5":
        return StochHelpResult(zone=zone, action="BOOST", score_delta=10, reason="stoch_boost")
    if zone == "Z4":
        return StochHelpResult(zone=zone, action="BOOST", score_delta=5, reason="stoch_boost")
    if zone in ("Z2", "Z3"):
        return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
    # Z1: VETO hard, PASS soft
    if effective_mode == "hard":
        return StochHelpResult(
            zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against"
        )
    return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
