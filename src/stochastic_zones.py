"""M15 stoch zone help over STRAT-F (pure, no I/O).

V3 (actualizacion completa): la regla de entrada en zonas extremas ya NO
es "BOOST ciego apenas el %K toca el extremo". Ahora exige
AGOTAMIENTO VERDADERO (ver stoch_exhaustion.evaluate_exhaustion):

  - CALL en Z1 (sobreventa): requiere cruce alcista CONFIRMADO (>=1 vela
    M15 de antiguedad) + vela de agotamiento (martillo/doji/estrellafugaz)
    en el soporte.
  - PUT en Z5 (sobrecompra): requiere cruce bajista CONFIRMADO +
    vela de agotamiento en la resistencia.

Si esta confirmado -> BOOST fuerte (+12).
Si falta (EXHAUST_WAIT) -> PASS (no entra, pero deja vigilar al fractal;
no es VETO duro: el par puede madurar y confirmar en la siguiente vela).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence

from stoch_exhaustion import evaluate_exhaustion

Zone = Literal["Z1", "Z2", "Z3", "Z4", "Z5"]
Action = Literal["BOOST", "PASS", "VETO"]
StochHelpMode = Literal["off", "soft", "hard"]

_VALID_MODES = frozenset({"off", "soft", "hard"})


@dataclass(frozen=True)
class StochHelpResult:
    zone: Optional[Zone]
    action: Action
    score_delta: int
    reason: str  # stoch_boost | stoch_pass | stoch_extreme_against | stoch_no_k | stoch_momentum_continuation | stoch_exhaust_wait | stoch_exhaust_confirmed
    exhaustion: Optional[object] = None  # ExhaustResult para auditoria


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
    stoch_full: Optional[dict] = None,
    candles_15m: Optional[Sequence] = None,
    zone_lo: Optional[float] = None,
    zone_hi: Optional[float] = None,
    stoch_m5: Optional[dict] = None,   # {k,d,estado,cruce} del M5 — debe alinearse
    zone_strength: Optional[float] = None,  # % fuerza linea imaginaria (zone_strength).
                                           # FUENTE PRINCIPAL de la banda (R7).
    candles_1m: Optional[Sequence] = None,  # ventana M1 para evaluacion INTRAVELA (R10)
    lookback: int = 3,                        # velas M1/15m a revisar para la vela de rechazo
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

    # --- V3: agotamiento verdadero en zonas extremas -------------------
    # Z1 (sobreventa) para CALL y Z5 (sobrecompra) para PUT son las
    # unicas zonas donde el rebote tiene sentido. En AMBAS exige el
    # agotamiento confirmado (cruce + vela de rechazo en la franja S/R).
    if (direction_u == "CALL" and zone == "Z1") or (
        direction_u == "PUT" and zone == "Z5"
    ):
        ex = evaluate_exhaustion(
            k=k,
            d=d,
            k_vals=stoch_full.get("k_vals") if stoch_full else None,
            d_vals=stoch_full.get("d_vals") if stoch_full else None,
            direction=direction_u,
            candles_15m=candles_15m,
            zone_lo=zone_lo,
            zone_hi=zone_hi,
            stoch_m5=stoch_m5,
            zone_strength=zone_strength,
            candles_1m=candles_1m,
            lookback=lookback,
        )
        if ex.action == "EXHAUST_CONFIRMED":
            return StochHelpResult(
                zone=zone, action="BOOST", score_delta=12,
                reason="stoch_exhaust_confirmed", exhaustion=ex,
            )
        # EXHAUST_WAIT: en la zona pero sin cruce confirmado y/o sin vela
        # de rechazo. No entra (PASS), pero NO es veto: el fractal sigue
        # vigilando y puede confirmar en la proxima vela M15.
        return StochHelpResult(
            zone=zone, action="PASS", score_delta=0,
            reason=f"stoch_exhaust_wait:{ex.reason}", exhaustion=ex,
        )

    # Zonas medias / no-extremas: comportamiento anterior (boost suave
    # a favor de la direccion, PASS en Z2/Z3/Z4 segun lado).
    if direction_u == "CALL":
        if zone == "Z2":
            return StochHelpResult(zone=zone, action="BOOST", score_delta=5, reason="stoch_boost")
        if zone in ("Z3", "Z4"):
            return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
        # Z5 (CALL): sobrecompra es contra-direccion -> vetar si confirma
        if effective_mode == "hard":
            if _is_cross_against(k, k_prev, d, "CALL"):
                return StochHelpResult(zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against")
            if _is_momentum_continuing(k, k_prev, "CALL"):
                return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_momentum_continuation")
            return StochHelpResult(zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against")
        return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")

    # PUT
    if zone == "Z4":
        return StochHelpResult(zone=zone, action="BOOST", score_delta=5, reason="stoch_boost")
    if zone in ("Z2", "Z3"):
        return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
    # Z1 (PUT): sobreventa es contra-direccion -> vetar si confirma
    if effective_mode == "hard":
        if _is_cross_against(k, k_prev, d, "PUT"):
            return StochHelpResult(zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against")
        if _is_momentum_continuing(k, k_prev, "PUT"):
            return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_momentum_continuation")
        return StochHelpResult(zone=zone, action="VETO", score_delta=0, reason="stoch_extreme_against")
    return StochHelpResult(zone=zone, action="PASS", score_delta=0, reason="stoch_pass")
