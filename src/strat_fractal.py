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
from config import STRAT_F_MIN_PAYOUT, STRAT_F_MIN_SCORE, STRAT_F_ZONE_MIN_AGE


@dataclass
class StratFEvaluation:
    has_signal: bool = False
    direction: Optional[str] = None          # "CALL" | "PUT"
    entry_mode: str = "REBOUND"
    zone: Optional[ConsolidationZone] = None
    pattern_name: str = "none"               # "fractal_up" | "fractal_down"
    strength: float = 0.0
    confirms: bool = False
    skip_reason: Optional[str] = None
    m15_context: str = "unknown"             # "range" | "uptrend" | "downtrend" | "broken"
    m5_event: str = "none"                   # "fractal_up" | "fractal_down" | "none"
    info: str = ""


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
    """Contexto M15: range / uptrend / downtrend / broken.

    'broken' = el tramo previo era un rango lateral (estreo) y la ultima vela
    lo rompio con cuerpo (no operamos rebotes en ese caso).
    'range'  = rango estrecho sin tendencia.
    'uptrend'/'downtrend' = movimiento claro de cierre primero->ultimo.
    """
    if len(candles_15m) < 6:
        return "unknown"
    recent = candles_15m[-6:]
    last = recent[-1]
    prev = recent[:-1]
    prev_hi = max(c.high for c in prev)
    prev_lo = min(c.low for c in prev)
    prev_mid = (prev_hi + prev_lo) / 2.0
    prev_rng_pct = (prev_hi - prev_lo) / prev_mid if prev_mid else 0.0
    body = abs(last.close - last.open)

    # Ruptura de un rango lateral previo
    if prev_rng_pct < 0.004:
        if last.close > prev_hi and body > 0:
            return "broken"
        if last.close < prev_lo and body > 0:
            return "broken"

    # Tendencia / rango sobre una ventana mas amplia (las velas disponibles)
    trend = candles_15m[-12:] if len(candles_15m) >= 12 else candles_15m
    first_close = trend[0].close
    last_close = trend[-1].close
    move_pct = (last_close - first_close) / first_close if first_close else 0.0
    if move_pct > 0.006:
        return "uptrend"
    if move_pct < -0.006:
        return "downtrend"
    return "range"


def _m1_rejects_band(candles_1m: List[Candle], band: float, direction: str, tolerance_pct: float = 0.0010) -> bool:
    """M1 (menor) rechaza la banda: la mecha toca la banda pero el cierre NO queda fuera.

    Para CALL (banda = suelo): la vela debe tocar cerca del suelo (mecha inferior)
    y cerrar POR ENCIMA de la banda (rechazo alcista).
    Para PUT (banda = techo): la vela debe tocar cerca del techo (mecha superior)
    y cerrar POR DEBAJO de la banda (rechazo bajista).
    """
    if not candles_1m:
        return False
    last = candles_1m[-1]
    tol = band * tolerance_pct
    if direction == "CALL":
        touched = last.low <= band + tol
        closed_ok = last.close > band
        return touched and closed_ok
    if direction == "PUT":
        touched = last.high >= band - tol
        closed_ok = last.close < band
        return touched and closed_ok
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


def evaluate_strat_f(
    candles_15m: List[Candle],
    candles_5m: List[Candle],
    candles_1m: List[Candle],
    payout: int = 80,
    *,
    min_payout: int = STRAT_F_MIN_PAYOUT,
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

    # R6 — score minimo
    if strength * 100 < min_score:
        return StratFEvaluation(
            has_signal=False, m15_context=ctx, m5_event=event,
            strength=strength, skip_reason=f"score {strength*100:.0f} < minimo {min_score}",
        )

    zone = ConsolidationZone(
        asset=getattr(candles_5m[-1], "asset", "") if hasattr(candles_5m[-1], "asset") else "",
        ceiling=band if direction == "PUT" else band,
        floor=band if direction == "CALL" else band,
        bars_inside=0,
        detected_at=candles_5m[-1].ts if hasattr(candles_5m[-1], "ts") else 0.0,
        range_pct=0.0,
    )
    return StratFEvaluation(
        has_signal=True,
        direction=direction,
        entry_mode="REBOUND",
        zone=zone,
        pattern_name=event,
        strength=strength,
        confirms=True,
        m15_context=ctx,
        m5_event=event,
        info=f"STRAT-F {direction} banda={band:.5f} ctx={ctx}",
    )
