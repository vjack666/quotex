"""M15 stoch zone help over STRAT-F (pure, no I/O).

V2: Zone vetos now consider cross direction — only veto when the cross
CONFIRMS the extreme is turning against us. Momentum continuation in
extreme zones is PASS, not VETO.
"""
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
    reason: str  # stoch_boost | stoch_pass | stoch_extreme_against | stoch_no_k | stoch_momentum_continuation


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


def _is_cross_against(k: float, k_prev: float, d: Optional[float], direction: str) -> bool:
    """Check if the stoch cross is turning AGAINST the intended direction.
    
    CALL wants upward momentum → cross against = %K crossing DOWN through %D in OB zone.
    PUT wants downward momentum → cross against = %K crossing UP through %D in OS zone.
    """
    if d is None or k_prev is None:
        return False
    
    if direction == "CALL":
        # Bearish cross in overbought: k_prev >= d and now k < d (turning down)
        # This is the dangerous one — stoch says "momentum dying" in OB
        return k_prev >= d and k < d
    if direction == "PUT":
        # Bullish cross in oversold: k_prev <= d and now k > d (turning up)
        return k_prev <= d and k > d
    
    return False


def _is_momentum_continuing(k: float, k_prev: float, direction: str) -> bool:
    """Check if momentum is continuing in the expected direction.
    
    CALL + Z5 (OB): if %K is still rising or flat → momentum continuation (good).
    PUT + Z1 (OS): if %K is still falling or flat → momentum continuation (good).
    """
    if k_prev is None:
        return False
    
    if direction == "CALL":
        return k >= k_prev  # %K still rising or flat in OB = momentum alive
    if direction == "PUT":
        return k <= k_prev  # %K still falling or flat in OS = momentum alive
    
    return False


def apply_stoch_help(
    k: Optional[float],
    direction: str,
    mode: str,
    *,
    k_prev: Optional[float] = None,
    d: Optional[float] = None,
) -> StochHelpResult:
    """Return zone/action/score_delta for STRAT-F direction.

    V2 changes:
    - VETO only fires when cross CONFIRMS reversal against us (not just being in zone).
    - Momentum continuation in extreme zones → PASS with a note.
    - k_prev and d enable cross detection (backward-compatible: if None, old behavior).

    - mode "off": always PASS, score_delta 0
    - mode "soft": boosts only; never VETO
    - mode "hard": boosts + VETO on confirmed reversal against us
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
        # Z5: Check cross direction before vetoing
        if effective_mode == "hard":
            if _is_cross_against(k, k_prev, d, "CALL"):
                return StochHelpResult(
                    zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against"
                )
            if _is_momentum_continuing(k, k_prev, "CALL"):
                return StochHelpResult(
                    zone=zone, action="PASS", score_delta=0, reason="stoch_momentum_continuation"
                )
            # k_prev not available or ambiguous → old behavior (conservative VETO)
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
    # Z1: Check cross direction before vetoing
    if effective_mode == "hard":
        if _is_cross_against(k, k_prev, d, "PUT"):
            return StochHelpResult(
                zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against"
            )
        if _is_momentum_continuing(k, k_prev, "PUT"):
            return StochHelpResult(
                zone=zone, action="PASS", score_delta=0, reason="stoch_momentum_continuation"
            )
        return StochHelpResult(
            zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against"
        )
    return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
