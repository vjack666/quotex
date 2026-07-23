"""Estrategia F: Fractal / Wyckoff (marco M15/M5/M1).

Une los libros de boblioteca/:
- wyckoff/  : entradas solo en bandas naranjas (zonas), M15 contexto / M5 estructura / M1 ejecucion.
- fractales/: fractal Bill Williams de 5 velas marca el giro.

Jerarquia fractal: la temporalidad MAYOR (M15) manda. Nunca operar una senal de
M1 que vaya contra M15. Alineacion M15+M5+M1 sube probabilidad.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from models import Candle, ConsolidationZone
from config import MIN_PAYOUT, STRAT_F_MIN_SCORE, STRAT_F_ZONE_MIN_AGE
from config import STRAT_F_SPIKE_MODE
from config import EXTREME_READ_BODY_MIN_RATIO

from stochastic_m15 import compute_stoch


@dataclass
class StratFEvaluation:
    has_signal: bool = False
    direction: Optional[str] = None          # "CALL" | "PUT"
    entry_mode: str = "REBOUND"
    zone: Optional[ConsolidationZone] = None
    pattern_name: str = "none"               # "fractal_up" | "fractal_down"
    strength: float = 0.0
    confirms: bool = False
    spike: bool = False               # True = entrada SPIKE (extremo con conviccion) por agotamiento
    skip_reason: Optional[str] = None
    m15_context: str = "unknown"             # "range" | "uptrend" | "downtrend" | "broken"
    m5_event: str = "none"                   # "fractal_up" | "fractal_down" | "none"
    info: str = ""
    spring_margin: "Optional[float]" = None        # heurística 5m/1m: margen % del precio post-fractal vs banda del fractal. Positivo=spring limpio, negativo=rompió. None=indeterminado. SOLO observación, NO bloquea.
    math_quality: "Optional[dict]" = None    # geometric analysis (hurst, r2, angle, squeeze)


def _fractal_up(candles: List[Candle], i: int) -> bool:
    """Fractal alcista (techo): maximo central mas alto que los 2 a cada lado."""
    if i < 2 or i > len(candles) - 3:
        return False
    h = candles[i].high
    return (
        h > candles[i - 1].high
        and h > candles[i - 2].high
        and h > candles[i + 1].high
        and h > candles[i + 2].high
    )


def _fractal_down(candles: List[Candle], i: int) -> bool:
    """Fractal bajista (suelo): minimo central mas bajo que los 2 a cada lado."""
    if i < 2 or i > len(candles) - 3:
        return False
    l = candles[i].low
    return (
        l < candles[i - 1].low
        and l < candles[i - 2].low
        and l < candles[i + 1].low
        and l < candles[i + 2].low
    )


def _m15_context(candles_15m: List[Candle]) -> str:
    """Contexto M15 via regresion lineal (geometric eyes, no magic numbers).
    
    Instead of hardcoded thresholds (0.004, 0.006), uses:
    - R² of the close price regression → measures if there's a real trend
    - Slope angle → measures direction and strength
    - Decision logic:
      * R² < 0.3 → "range" (no clear direction, noise dominates)
      * R² >= 0.3 AND slope angle > +2° → "uptrend"
      * R² >= 0.3 AND slope angle < -2° → "downtrend"
      * Check for breakout: last candle closes > 2 standard deviations
        from the regression line → "broken"
    """
    import math
    if len(candles_15m) < 6:
        return "unknown"
    
    recent = candles_15m[-12:] if len(candles_15m) >= 12 else candles_15m
    closes = [float(c.close) for c in recent]
    n = len(closes)
    
    # Linear regression on closes
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(closes) / n
    
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, closes))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if abs(den) > 1e-15 else 0.0
    intercept = mean_y - slope * mean_x
    
    # R² calculation
    ss_tot = sum((y - mean_y) ** 2 for y in closes)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, closes))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0
    r_squared = max(0.0, min(1.0, r_squared))
    
    # Slope as angle (normalized by price level for cross-asset comparison)
    if mean_y > 0:
        normalized_slope = slope / mean_y  # percentage change per candle
        angle_deg = math.degrees(math.atan(normalized_slope * 100))
    else:
        angle_deg = 0.0
    
    # Breakout detection: last candle vs regression band
    last_close = closes[-1]
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, closes)]
    std_residual = (sum(r ** 2 for r in residuals) / n) ** 0.5 if n > 1 else 0.0
    last_residual = residuals[-1]
    
    # Breakout: last residual exceeds 2σ of previous residuals' deviations.
    # This catches the case where previous candles were tightly clustered around
    # the regression line and the last candle jumps out.
    prev_residuals_std = (sum(r ** 2 for r in residuals[:-1]) / max(1, n - 1)) ** 0.5
    if prev_residuals_std > 0:
        is_broken_up = last_residual > 2.0 * prev_residuals_std
        is_broken_down = last_residual < -2.0 * prev_residuals_std
        if is_broken_up or is_broken_down:
            return "broken"
    elif std_residual > 0:
        # Fallback: if all previous residuals are exactly zero, any nonzero last = breakout
        if abs(last_residual) > 1e-10:
            return "broken"
    
    # Direction based on R² and angle
    if r_squared < 0.3:
        return "range"  # noise dominates, no clear trend
    
    # Threshold ~3° ≈ 0.6% move over 12 candles (matches old move_pct threshold)
    if angle_deg > 3.0:
        return "uptrend"
    if angle_deg < -3.0:
        return "downtrend"
    
    return "range"


def _m1_rejects_band(candles_1m: List[Candle], band: float, direction: str, tolerance_pct: float = 0.0015) -> bool:
    """M1 rechaza la banda: al menos 2 velas consecutivas muestran rechazo.

    Requisitos:
    - Ultima vela: mecha toca la banda, cierre del lado correcto.
    - Penultima vela: tambien toco la banda (o estuvo muy cerca) — confirma
      que el precio probo el nivel y fue rechazado, no fue un spike accidental.
    """
    if not candles_1m or len(candles_1m) < 2:
        return False

    last = candles_1m[-1]
    prev = candles_1m[-2]
    tol = band * tolerance_pct

    if direction == "CALL":
        # Last candle: touches band with wick, closes above
        last_touched = last.low <= band + tol
        last_closed_ok = last.close > band
        # Previous candle: also touched or was near the band (confirms the level)
        prev_near = prev.low <= band + tol * 2  # slightly wider tolerance for prev
        return last_touched and last_closed_ok and prev_near

    if direction == "PUT":
        last_touched = last.high >= band - tol
        last_closed_ok = last.close < band
        prev_near = prev.high >= band - tol * 2
        return last_touched and last_closed_ok and prev_near

    return False


def _avg_ticks(candles: List[Candle], n: int) -> float:
    window = candles[-n:] if len(candles) >= n else candles
    if not window:
        return 0.0
    vals = [c.ticks for c in window if c.ticks > 0]
    return sum(vals) / len(vals) if vals else 0.0


def _phase_a_from_ticks(candles_15m: List[Candle], direction: str) -> bool:
    """Fase A de Wyckoff vía ticks reales de M15.

    Climax de participacion (cuerpo grande + ticks altos sobre el promedio)
    seguido de absorcion (velas posteriores con cuerpo pequeno y pocos ticks).
    No es gate duro: devuelve True solo como refuerzo de fuerza.
    """
    if len(candles_15m) < 6:
        return False
    recent = candles_15m[-6:]
    avg_tk = _avg_ticks(candles_15m, 12)
    if avg_tk <= 0:
        return False  # ticks no disponibles en este par -> no evaluamos

    # Buscar el climax (no la ultima vela; dejamos margen a la absorcion)
    climax_idx = None
    for i in range(len(recent) - 1, 1, -1):
        c = recent[i]
        body = c.body
        if body > 0 and c.ticks >= avg_tk * 1.4:
            climax_idx = i
            break
    if climax_idx is None:
        return False

    # Absorcion: las velas tras el climax tienen cuerpo pequeño y pocos ticks
    after = recent[climax_idx + 1:]
    if not after:
        return False
    small = sum(1 for x in after if x.body < (recent[climax_idx].body * 0.5) and (x.ticks == 0 or x.ticks < avg_tk * 0.7))
    return small >= max(1, len(after) // 2)


def _spring_heuristic_5m1m(
    candles_5m: List[Candle],
    candles_1m: List[Candle],
    fractal_idx: int,
    band: float,
    direction: str,
) -> "Optional[float]":
    """Heurística OBSERVACIONAL de spring sobre la banda fractal.

    NO es el StochasticSpringDetector (SSD) real de SMC-SYSTEMS. Devuelve el
    MARGEN en % de la banda, no un bool:
    - CALL (fractal_down, band=low): margen = (min(low post-fractal) - band) / band * 100
        positivo = no rompió el suelo (spring más limpio cuanto más alto);
        negativo = sí rompió por debajo de la banda.
    - PUT (fractal_up, band=high): margen = (max(high post-fractal) - band) / band * 100
        positivo = no rompió el techo; negativo = rompió por encima.
    - Post-fractal = candles_5m[fractal_idx+1:fractal_idx+4]; si no hay suficientes
      (fractal_idx == last_idx), usa las últimas 2-3 velas 1m recientes.
    - Si tampoco alcanza -> None (NO forzar).

    Devuelve Optional[float] (porcentaje) o None. No altera ninguna decisión.
    """
    if direction == "CALL":
        # fractal_down: band = low del fractal. Buscamos si rompió el suelo.
        post_5m = candles_5m[fractal_idx + 1: fractal_idx + 4]
        if len(post_5m) >= 1:
            post_min = min(c.low for c in post_5m)
            return (post_min - band) / band * 100.0
        rec_1m = candles_1m[-3:] if len(candles_1m) >= 3 else candles_1m
        if len(rec_1m) >= 2:
            post_min = min(c.low for c in rec_1m)
            return (post_min - band) / band * 100.0
        return None
    elif direction == "PUT":
        # fractal_up: band = high del fractal. Buscamos si rompió el techo.
        post_5m = candles_5m[fractal_idx + 1: fractal_idx + 4]
        if len(post_5m) >= 1:
            post_max = max(c.high for c in post_5m)
            return (post_max - band) / band * 100.0
        rec_1m = candles_1m[-3:] if len(candles_1m) >= 3 else candles_1m
        if len(rec_1m) >= 2:
            post_max = max(c.high for c in rec_1m)
            return (post_max - band) / band * 100.0
        return None
    return None


def evaluate_strat_f(
    candles_15m: List[Candle],
    candles_5m: List[Candle],
    candles_1m: List[Candle],
    payout: int = 80,
    *,
    min_payout: int = MIN_PAYOUT,
    min_score: float = STRAT_F_MIN_SCORE,
    zone_min_age: int = STRAT_F_ZONE_MIN_AGE,
) -> StratFEvaluation:
    """Evaluador puro STRAT-F (sin I/O).

    1. M15 define contexto (la mayor manda).
    2. M5 busca fractal Bill Williams en una banda (zona Wyckoff).
    3. M1 confirma el rechazo en la banda.

    Filtros de calidad (SDD strat_f_quality_validation):
    - R2 payout minimo, R3 edad minima de zona, R6 score minimo.
    """
    # R2 — payout minimo
    if payout < min_payout:
        return StratFEvaluation(has_signal=False, m15_context="unknown",
                                skip_reason=f"payout {payout}% < minimo {min_payout}%")

    ctx = _m15_context(candles_15m)
    if ctx == "broken":
        return StratFEvaluation(has_signal=False, m15_context=ctx, skip_reason="M15 rango roto: no operar rebotes")
    if len(candles_5m) < 5:
        return StratFEvaluation(has_signal=False, m15_context=ctx, skip_reason="M5 insuficiente para fractal")

    # Buscar el fractal mas reciente en M5
    last_idx = len(candles_5m) - 3
    event = "none"
    band = 0.0
    fractal_idx = -1
    direction: Optional[str] = None
    for i in range(last_idx, 1, -1):
        if _fractal_down(candles_5m, i):
            event = "fractal_down"
            band = candles_5m[i].low
            direction = "CALL"   # suelo tocado -> rebote alcista
            fractal_idx = i
            break
        if _fractal_up(candles_5m, i):
            event = "fractal_up"
            band = candles_5m[i].high
            direction = "PUT"    # techo tocado -> rebote bajista
            fractal_idx = i
            break

    if event == "none":
        return StratFEvaluation(has_signal=False, m15_context=ctx, m5_event="none", skip_reason="sin fractal M5 en banda")

    # R3 — edad minima de la zona/banda (velas M5 desde el fractal a la ultima)
    bars_since_fractal = (len(candles_5m) - 1) - fractal_idx
    if bars_since_fractal < zone_min_age:
        return StratFEvaluation(
            has_signal=False, m15_context=ctx, m5_event=event,
            skip_reason=f"zona muy joven ({bars_since_fractal} < {zone_min_age} velas M5)",
        )

    assert direction is not None  # event != "none" implica direction seteado

    # Alineacion de contexto M15 con la direccion propuesta (R1)
    if ctx == "downtrend" and direction == "CALL":
        return StratFEvaluation(has_signal=False, m15_context=ctx, m5_event=event, skip_reason="CALL contra tendencia M15")
    if ctx == "uptrend" and direction == "PUT":
        return StratFEvaluation(has_signal=False, m15_context=ctx, m5_event=event, skip_reason="PUT contra tendencia M15")

    # M1 confirma el rechazo en la banda (R4)
    if not _m1_rejects_band(candles_1m, band, direction):
        return StratFEvaluation(
            has_signal=False, m15_context=ctx, m5_event=event,
            skip_reason="M1 no rechaza la banda (cierra fuera)",
        )

    # Fase A de Wyckoff (climax + absorcion) usando ticks reales de M15.
    # No es un gate duro: solo refuerza la fuerza si el contexto M15 viene de
    # un climax de participacion seguido de absorcion (cuerpos pequeños, pocos ticks).
    phase_a = _phase_a_from_ticks(candles_15m, direction)
    strength = 0.7 if ctx == "range" else 0.55
    if phase_a:
        strength = min(1.0, strength + 0.15)

    # ── Math/trig signal quality (geometric "eyes") ──
    # Contextual modifier: proportional zones + M15 weight + consensus bonus.
    mq = None
    try:
        from math_filters import compute_contextual_modifier
        cm = compute_contextual_modifier(candles_5m, direction, ctx)
        mq = cm  # store for StratFEvaluation.math_quality
        strength = max(0.1, min(1.0, strength + cm["delta"]))
    except Exception:
        pass  # math filters are soft — never block

    # R6 — score minimo
    if strength * 100 < min_score:
        return StratFEvaluation(
            has_signal=False, m15_context=ctx, m5_event=event,
            strength=strength, skip_reason=f"score {strength*100:.0f} < minimo {min_score}",
        )

    # Compute Wyckoff band as a RANGE (not a single price).
    # Use the fractal candle's range as the zone width.
    _fc = candles_5m[fractal_idx]
    _fc_range = abs(float(_fc.high) - float(_fc.low))
    if direction == "CALL":
        _zone_floor = float(_fc.low)
        _zone_ceil = float(_fc.low) + _fc_range * 0.5  # upper half of fractal candle
    else:
        _zone_ceil = float(_fc.high)
        _zone_floor = float(_fc.high) - _fc_range * 0.5  # lower half of fractal candle
    _zone_range_pct = _fc_range / _zone_floor if _zone_floor > 0 else 0.0

    zone = ConsolidationZone(
        asset=getattr(candles_5m[-1], "asset", "") if hasattr(candles_5m[-1], "asset") else "",
        ceiling=_zone_ceil,
        floor=_zone_floor,
        bars_inside=0,
        detected_at=candles_5m[-1].ts if hasattr(candles_5m[-1], "ts") else 0.0,
        range_pct=_zone_range_pct,
    )
    spring_margin = _spring_heuristic_5m1m(
        candles_5m, candles_1m, fractal_idx, band, direction
    )
    _mq_info = ""
    if mq is not None:
        _mq_info = f" math=[{mq['zone']} Δ={mq['delta']:+.3f} cons={mq['consensus_count']}/4 w={mq['m15_weight']}]"
    # ── Condición SPIKE (adicional al rebote, NO lo reemplaza) ──
    # Cuando hay patrón de agotamiento (stoch M5 exhaust) y el precio toca el
    # extremo del fractal (band) con CUERPO a FAVOR de la dirección, promueve
    # la señal a modo SPIKE: entra EN el extremo (CALL en mínimo, PUT en máximo)
    # — el spike con convicción — en vez de esperar el rebote en la banda.
    # El rebote sigue siendo la señal base cuando no hay agotamiento.
    entry_mode = "REBOUND"
    is_spike = False
    if STRAT_F_SPIKE_MODE:
        _stoch = compute_stoch(candles_5m, k_period=14, d_period=3)
        _k = (_stoch or {}).get("k") if _stoch else None
        if stoch_m5_exhausted(_k, direction):
            _entry_candle = candles_1m[-1] if candles_1m else candles_5m[-1]
            _entry_px = _entry_candle.close
            _near_extreme = abs(float(_entry_px) - float(band)) <= float(band) * 0.0015
            _body = float(_entry_candle.close) - float(_entry_candle.open)
            _body_toward = (_body > 0) if direction == "CALL" else (_body < 0)
            _body_ratio = abs(_body) / max(float(_entry_candle.high) - float(_entry_candle.low), 1e-9)
            if _near_extreme and _body_toward and _body_ratio >= EXTREME_READ_BODY_MIN_RATIO:
                entry_mode = "SPIKE"
                is_spike = True

    return StratFEvaluation(
        has_signal=True,
        direction=direction,
        entry_mode=entry_mode,
        zone=zone,
        pattern_name=event,
        strength=strength,
        confirms=True,
        spike=is_spike,
        m15_context=ctx,
        m5_event=event,
        spring_margin=spring_margin,
        math_quality=mq,
        info=f"STRAT-F {direction} banda={band:.5f} ctx={ctx} mode={entry_mode}{_mq_info}",
    )


def recheck_m15_alignment(candles_15m: List[Candle], direction: str) -> bool:
    """Re-evaluación de la alineación M15 ACTUAL al promover desde maturing_watchlist.

    Devuelve True si la dirección propuesta está ALINEADA con el contexto M15
    actual (no contra-tendencia). False si quedó contra-tendencia
    (M15=downtrend & CALL, o M15=uptrend & PUT). Esto es R1/R5 del spec
    #16: la promoción debe usar el contexto de AHORA, no el de la detección.
    """
    ctx = _m15_context(candles_15m)
    if ctx == "downtrend" and direction == "CALL":
        return False
    if ctx == "uptrend" and direction == "PUT":
        return False
    return True


def stoch_m5_exhausted(stoch_k: Optional[float], direction: str) -> bool:
    """Confirmación de agotamiento del contra-movimiento (R3 del spec #16).

    CALL contra-M15-bajista  -> stoch M5 %K < 20 (sobreventa = el impulso
                                            bajista se agotó).
    PUT contra-M15-alcista   -> stoch M5 %K > 80 (sobrecompra = el impulso
                                            alcista se agotó).
    Cualquier otro caso (None, contra-tendencia sin extremo) -> False.
    """
    if stoch_k is None:
        return False
    if direction == "CALL":
        return stoch_k < 20.0
    if direction == "PUT":
        return stoch_k > 80.0
    return False


def extreme_read_gate(
    candles: List[Candle],
    entry_price: Optional[float],
    direction: str,
    *,
    extreme_pos: float = 0.15,
    body_min_ratio: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """Lee la vela de ENTRADA cuando cae en el EXTREMO del rango local.

    El extremo NO es el enemigo (es el mejor sitio, como entrar en un spike).
    El riesgo es operar el REBOTE en lugar del quiebre: la vela de entrada
    cerró contra la dirección esperada (el precio ya devolvió).

    Criterio (empírico en black-box: PUT ganadoras en mínimo tenían 100%
    cuerpo confirmando bajada; PUT perdedoras solo 67%):
      - Si el entry NO está en el extremo del rango local -> gate ABIERTO (True).
      - Si está en el extremo:
          * la vela de entrada debe tener CUERPO a FAVOR de la dirección
            (CALL: close>open; PUT: close<open) y cuerpo dominante
            (|cuerpo| >= body_min_ratio * rango de la vela).
          * => True ("extreme_read_ok"): es spike con convicción.
          * sino => False ("extreme_read_reject:body_against"): es rebote.

    `used` lo marca el caller para la black-box (cuándo el gate efecivamente
    decidíó la señal). Esta función es pura: no toca DB ni red.
    """
    if not candles or entry_price in (None, 0):
        return True, None  # sin contexto -> no bloqueamos
    try:
        e = float(entry_price)
        highs = [float(c.high) for c in candles if getattr(c, "high", None) is not None]
        lows = [float(c.low) for c in candles if getattr(c, "low", None) is not None]
    except (TypeError, ValueError):
        return True, None
    if not highs or not lows:
        return True, None
    lo, hi = min(lows), max(highs)
    if hi <= lo:
        return True, None
    pos = (e - lo) / (hi - lo)
    in_extreme = (direction == "CALL" and pos > 1.0 - extreme_pos) or (
        direction == "PUT" and pos < extreme_pos
    )
    if not in_extreme:
        return True, None  # entry centrada -> no aplica lectura de extremo

    # Vela de entrada = la que contiene el entry en su rango
    entry_candle = None
    for c in candles:
        if float(getattr(c, "low", float("inf"))) <= e <= float(getattr(c, "high", float("-inf"))):
            entry_candle = c
            break
    if entry_candle is None:
        entry_candle = candles[-1]

    o = float(getattr(entry_candle, "open", e))
    cl = float(getattr(entry_candle, "close", e))
    body = abs(cl - o)
    rng = float(getattr(entry_candle, "high", e)) - float(getattr(entry_candle, "low", e))
    body_ratio = body / rng if rng > 0 else 0.0
    body_favors = (cl > o) if direction == "CALL" else (cl < o)

    if body_favors and body_ratio >= body_min_ratio:
        return True, "extreme_read_ok"
    return False, "extreme_read_reject:body_against"
