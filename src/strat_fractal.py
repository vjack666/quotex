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
from config import STRAT_F_SPIKE_OBSERVE
from config import EXTREME_READ_BODY_MIN_RATIO
from config import STOCH_HELP_MODE
from config import STRAT_F_FRENO_BRAIN

from stochastic_m15 import compute_stoch
from stochastic_zones import apply_stoch_help
from stoch_early_alert import evaluate_early_alert  # capa de alerta temprana (R-EA)
from stoch_cross_state import StochCrossState


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
    wyckoff_event: "Optional[str]" = None    # Fase A Wyckoff: "spring" (CALL en suelo) / "upthrust" (PUT en techo) / None
    exhaustion_candle: "Optional[str]" = None  # vela de rechazo: "martillo"/"doji"/"estrellafugaz"/"atrapado" / None
    separation_ok: "Optional[bool]" = None    # R2-bis: separacion %K/%D abierta tras cruce (adaptativa)
    separation_rel: "Optional[float]" = None  # |K-D| actual / max(|K-D| reciente) del propio oscilador
    decision: "Optional[str]" = None         # "OBSERVE" cuando el SPIKE está en modo observación (no opera)
    spike_observe: "Optional[dict]" = None   # desglose de las 6 condiciones del spec (modo observación)
    early_alert: "Optional[dict]" = None     # R-EA7: marca de alerta temprana (AJENA a has_signal); puro aviso
    ob_cross_idx: "Optional[int]" = None     # idx del primer cruce K/D bajista post-overbought en M15
    ob_cross_ago: "Optional[int]" = None     # velas M15 desde el cruce hasta el final de la serie
    stoch_k_last: "Optional[float]" = None   # último %K M15 disponible (trazabilidad)
    stoch_d_last: "Optional[float]" = None   # último %D M15 disponible (trazabilidad)


from math_utils import fractal_up as _fractal_up, fractal_down as _fractal_down


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


def _require_ob_cross(
    k_vals: list[float],
    d_vals: list[float],
    direction: str,
) -> "Optional[int]":
    """Gate forense: exige que el estocástico haya visitado el extremo y luego
    haya cruzado K/D en la dirección de entrada. Solo el primer cruce válido
    post-extremo cuenta.

    - PUT / freno_rebound: K tuvo que tocar >=80, luego cruzar K<D (bajista).
    - CALL / suelo: K tuvo que tocar <=20, luego cruzar K>D (alcista).
    """
    if not k_vals or not d_vals:
        return None
    n = min(len(k_vals), len(d_vals))
    target_extreme = 80.0 if direction == "PUT" else 20.0
    cross_confirmed = (
        (lambda i: i > 0 and k_vals[i - 1] >= d_vals[i - 1] and k_vals[i] < d_vals[i])
        if direction == "PUT"
        else (lambda i: i > 0 and k_vals[i - 1] <= d_vals[i - 1] and k_vals[i] > d_vals[i])
    )
    touched_extreme = False
    for idx in range(n):
        k = k_vals[idx]
        d = d_vals[idx]
        if k is None or d is None:
            continue
        if direction == "PUT" and k >= target_extreme:
            touched_extreme = True
        elif direction == "CALL" and k <= target_extreme:
            touched_extreme = True
        if touched_extreme and cross_confirmed(idx):
            return idx
    return None


def _run_freno_brain(
    candles_15m: List[Candle],
    *,
    stoch_m15: Optional[dict] = None,
    payout: int = 80,
    min_score: float = STRAT_F_MIN_SCORE,
    sym: Optional[str] = None,
) -> "Optional[StratFEvaluation]":
    """Ejecuta el motor de leyes (freno = cerebro) y traduce a StratFEvaluation.

    Lazy-import de strategy_lab para no acoplar el bot al laboratorio: si
    strategy_lab no está disponible, retorna None y STRAT-F cae al fractal
    clásico (graceful). Construye el LawContext desde las velas M15 y el
    stoch que ya trae el scanner.

    Retorna:
    - StratFEvaluation(has_signal=True, ...) si el motor decide entrar.
    - StratFEvaluation(has_signal=False, skip_reason=...) si el motor bloquea.
    - None si no puede evaluar (datos insuficientes / import fallido) → el
      caller (evaluate_strat_f) cae al fractal clásico.
    """
    if not candles_15m or len(candles_15m) < 35:
        return None
    try:
        from strategy_lab.law_engine import LawContext, LawEngine
        from strategy_lab.laws_freno import (
            FrenoConfig, build_freno_laws,
        )
    except Exception:
        return None  # strategy_lab ausente -> fractal clasico

    import numpy as np
    o = np.array([float(c.open) for c in candles_15m], float)
    h = np.array([float(c.high) for c in candles_15m], float)
    l = np.array([float(c.low) for c in candles_15m], float)
    c = np.array([float(c.close) for c in candles_15m], float)

    cfg = FrenoConfig()
    # Pesos semilla: el Discovery los sobreescribe cuando mine las leyes.
    # Mientras tanto, pesos proporcionales a la evidencia ya validada.
    seed_weights = {
        "FRENO-IMPULSO-MUERTO": 40.0,
        "STOCH-EXTREMO": 20.0,
        "SEPARACION-KD": 15.0,
        "ZONA-HTF": 10.0,
        "RECHAZO-M1": 5.0,
    }
    laws = build_freno_laws(cfg, lambda lid, d: seed_weights.get(lid, d))
    eng = LawEngine(laws, lambda lid, d: seed_weights.get(lid, d))
    ctx = LawContext(o15=o, h15=h, l15=l, c15=c, stoch_m15=stoch_m15 or {}, sym=sym)
    res = eng.evaluate(ctx)
    if not res.ok:
        return StratFEvaluation(
            has_signal=False,
            m15_context="IMPULSE_DYING",
            m5_event="freno",
            direction=res.direction,
            skip_reason=f"freno:{res.failed_at} " + (res.detail or ""),
            info=f"FRENO-BRAIN bloqueado por {res.failed_at}: {res.detail}",
        )
    # ── GATE ESTRICTO: cruce K/D bajista post-entry para PUT (orden temporal 4→6) ──
    # Exigimos evidencia forense de que K superó >=80 y luego cruzó a la baja.
    _m15_k = (stoch_m15 or {}).get("k_vals") or []
    _m15_d = (stoch_m15 or {}).get("d_vals") or []
    _ob_cross = _require_ob_cross(_m15_k, _m15_d, direction or "")
    if _ob_cross is None:
        return StratFEvaluation(
            has_signal=False,
            m15_context="IMPULSE_DYING",
            m5_event="freno",
            direction=res.direction,
            skip_reason="stoch_no_ob_cross",
            info="FRENO-BRAIN bloqueado: falta cruce K/D post-overbought para PUT",
        )
    # Señal: normaliza la confianza (suma de pesos) a strength 0-1.
    max_conf = sum(seed_weights.values())
    strength = max(0.1, min(1.0, res.confianza / max_conf))
    # R6 — score minimo (igual que el fractal clasico)
    if strength * 100 < min_score:
        return StratFEvaluation(
            has_signal=False,
            m15_context="IMPULSE_DYING",
            m5_event="freno",
            direction=res.direction,
            strength=strength,
            skip_reason=f"score freno {strength*100:.0f} < minimo {min_score}",
            info=f"FRENO-BRAIN score {strength*100:.0f} < {min_score}",
        )
    # Zona simple alrededor del nivel actual para que el bot tenga contexto.
    lvl = float(c[-1])
    zone = ConsolidationZone(
        asset=sym or "",
        ceiling=lvl * 1.001,
        floor=lvl * 0.999,
        bars_inside=0,
        detected_at=getattr(candles_15m[-1], "ts", 0.0),
        range_pct=0.002,
    )
    _freno_last_ts = getattr(candles_15m[-1], "ts", 0.0)
    StochCrossState.get().register_cross(
        asset=sym or "",
        direction=res.direction or "",
        idx=_ob_cross,
        k_last=float((stoch_m15 or {}).get("k") or _m15_k[-1]),
        d_last=float((stoch_m15 or {}).get("d") or _m15_d[-1]),
        ts=str(_freno_last_ts) if _freno_last_ts is not None else None,
    )
    return StratFEvaluation(
        has_signal=True,
        direction=res.direction,
        entry_mode="REBOUND",
        zone=zone,
        pattern_name="freno_rebound",
        strength=strength,
        confirms=True,
        m15_context="IMPULSE_DYING",
        m5_event="freno",
        ob_cross_idx=_ob_cross,
        ob_cross_ago=len(_m15_k) - 1 - _ob_cross,
        stoch_k_last=float((stoch_m15 or {}).get("k") or _m15_k[-1]),
        stoch_d_last=float((stoch_m15 or {}).get("d") or _m15_d[-1]),
        info=f"FRENO-BRAIN OK leyes={res.passed} conf={res.confianza:.0f} dir={res.direction}",
    )


def evaluate_strat_f(
    candles_15m: List[Candle],
    candles_5m: List[Candle],
    candles_1m: List[Candle],
    payout: int = 80,
    *,
    min_payout: int = MIN_PAYOUT,
    min_score: float = STRAT_F_MIN_SCORE,
    zone_min_age: int = STRAT_F_ZONE_MIN_AGE,
    stoch_m5: Optional[dict] = None,        # {k,d,cruce} M5 — debe alinearse (R3)
    zone_strength: Optional[float] = None,  # % fuerza linea imaginaria (R7)
    stoch_m15: Optional[dict] = None,       # {k,d,k_vals,d_vals} M15 — si el scanner
                                            # lo pasa se reusa; si no, se calcula interno.
    sym: Optional[str] = None,              # símbolo del par (persistencia ALT B de la alerta)
    freno_brain: Optional[bool] = None,     # override de STRAT_F_FRENO_BRAIN (tests)
) -> StratFEvaluation:
    """Evaluador puro STRAT-F (sin I/O).

    1. M15 define contexto (la mayor manda).
    2. M5 busca fractal Bill Williams en una banda (zona Wyckoff).
    3. M1 confirma el rechazo en la banda.

    CEREBRO DE FRENO (Ruben 2026-07-28): si STRAT_F_FRENO_BRAIN (o freno_brain
    override) está ON, STRAT-F YA NO manda el fractal. Delega en el motor de
    leyes (law_engine): la Ley #1 (freno / muerte del impulso M15) es el
    disparador; el fractal queda como filtro secundario dentro de las leyes.
    El scanner sigue consumiendo StratFEvaluation igual — no cambia el bot.

    Filtros de calidad (SDD strat_f_quality_validation):
    - R2 payout minimo, R3 edad minima de zona, R6 score minimo.
    """
    _use_freno = freno_brain if freno_brain is not None else STRAT_F_FRENO_BRAIN

    # R2 — payout minimo
    if payout < min_payout:
        return StratFEvaluation(has_signal=False, m15_context="unknown",
                                skip_reason=f"payout {payout}% < minimo {min_payout}%")

    # CEREBRO DE FRENO: el motor de leyes manda. Si corre y decide, retorna.
    if _use_freno:
        r = _run_freno_brain(
            candles_15m, stoch_m15=stoch_m15, payout=payout, min_score=min_score,
            sym=sym,
        )
        if r is not None:
            return r

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

    # OB cross hard gate (classic path only; freno already checks inside)
    if not _use_freno:
        _m15_k = (stoch_m15 or {}).get("k_vals") or []
        _m15_d = (stoch_m15 or {}).get("d_vals") or []
        if len(_m15_k) < 2 or len(_m15_d) < 2 or len(_m15_k) != len(_m15_d):
            return StratFEvaluation(
                has_signal=False,
                m15_context=ctx,
                m5_event=event,
                direction=direction,
                skip_reason="stoch_m15_missing",
                info="STRAT-F bloqueado: datos M15 incompletos para verificar cruce",
                stoch_k_last=(_m15_k[-1] if _m15_k else None),
                stoch_d_last=(_m15_d[-1] if _m15_d else None),
            )
        _ob_cross = _require_ob_cross(_m15_k, _m15_d, direction or "")
        if _ob_cross is None:
            return StratFEvaluation(
                has_signal=False,
                m15_context=ctx,
                m5_event=event,
                direction=direction,
                skip_reason="stoch_no_ob_cross",
                info="STRAT-F bloqueado: falta cruce K/D post-overbought",
                stoch_k_last=_m15_k[-1],
                stoch_d_last=_m15_d[-1],
            )

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
    # ── ZONE STRENGTH (R7, fuente principal de la banda) ──
    # Si el caller no lo paso, lo calculamos sobre la ZONA S/R del fractal
    # (puro, sin I/O: recorre candles_15m). La "linea imaginaria" manda.
    if zone_strength is None and candles_15m is not None:
        try:
            from zone_strength import compute_support_efficacy
            _zl = float(zone.floor) if direction == "CALL" else float(zone.ceiling)
            _eff = compute_support_efficacy(_zl, candles_15m, direction=direction)
            zone_strength = _eff.get("efficacy")
        except Exception:
            zone_strength = None
    # ── Condición SPIKE mejorada (adicional al rebote, NO lo reemplaza) ──
    # Reusa stoch_exhaustion vía apply_stoch_help como motor (R1-R4, R4-bis):
    # agotamiento verdadero en la ZONA S/R del fractal con cruce M15 confirmado
    # + M5 alineado + vela de rechazo (o atrapado en extremo). Intravela: la
    # última vela de candles_15m es la M15 EN CURSO; candles_1m (ventana M1)
    # permite detectar el agotamiento DENTRO de la vela viva (R10, lookback=15).
    # Mapea a Fase A de Wyckoff: spring (CALL en suelo) / upthrust (PUT en techo).
    # DECISIÓN DOCUMENTADA (D5): reemplaza el "cuerpo a favor >= ratio" del
    # SPIKE viejo por classify_exhaustion_candle (martillo/doji/estrellafugaz)
    # porque la mecha de rechazo marca el rechazo real — más preciso, no es
    # pérdida accidental de comportamiento.
    entry_mode = "REBOUND"
    is_spike = False
    wyckoff_event: Optional[str] = None
    exhaustion_candle: Optional[str] = None
    separation_ok: Optional[bool] = None
    separation_rel: Optional[float] = None
    ea_dict: Optional[dict] = None  # marca de alerta temprana (R-EA), puro aviso
    if STRAT_F_SPIKE_MODE:
        # Reusa el stoch M15 que paso el scanner; si no, lo calcula interno
        # (fallback, p.ej. en tests que mockean strat_fractal.compute_stoch).
        _stoch_m15 = stoch_m15 if isinstance(stoch_m15, dict) else compute_stoch(candles_15m, direction=direction)
        _help = apply_stoch_help(
            (_stoch_m15 or {}).get("k"),
            direction,
            STOCH_HELP_MODE if STOCH_HELP_MODE in ("off", "soft", "hard") else "hard",
            stoch_full=_stoch_m15 if isinstance(_stoch_m15, dict) else None,
            candles_15m=candles_15m,        # última vela = M15 abierta (intravela)
            candles_1m=candles_1m,
            lookback=15,                    # 15 velas M1 = vida de la M15 abierta
            zone_lo=float(zone.floor),
            zone_hi=float(zone.ceiling),
            stoch_m5=stoch_m5,
            zone_strength=zone_strength,
        )
        # Separacion %K/%D (R2-bis) se propaga SIEMPRE que el motor devuelva
        # un ExhaustResult, sea BOOST o EXHAUST_WAIT (la caja negra debe ver
        # "cruce pegajoso" aunque no promueva a SPIKE).
        _ex = _help.exhaustion
        # --- Capa de ALERTA TEMPRANA (R-EA): marca de atención INTRAVELA ---
        # Evaluada sobre stoch_m15 (k_vals/d_vals) + candles_1m lookback=15.
        # NO altera has_signal ni entry_mode: es puro aviso (R-EA1/R-EA2/R-EA7).
        ea_dict = None
        if direction is not None:
            _ea_k = (stoch_m15 or {}).get("k_vals")
            _ea_d = (stoch_m15 or {}).get("d_vals")
            try:
                _ea_res = evaluate_early_alert(
                    direction, k_vals=_ea_k, d_vals=_ea_d,
                    candles_15m=candles_15m, candles_1m=candles_1m, sym=sym or "",
                )
                ea_dict = {
                    "activa": _ea_res.activa,
                    "reason": _ea_res.reason,
                    "pendiente_k": _ea_res.pendiente_k,
                    "pendiente_d": _ea_res.pendiente_d,
                    "aceleracion": _ea_res.aceleracion,
                    "angulo": _ea_res.angulo,
                    "proyeccion_velas": _ea_res.proyeccion_velas,
                    "convergencia": _ea_res.convergencia,
                    "puntaje": _ea_res.puntaje,
                    "percentil_par": _ea_res.percentil_par,
                    "ventana_proy": _ea_res.ventana_proy,
                    "es_default": _ea_res.es_default,
                }
            except Exception:
                ea_dict = None

        if _ex is not None:
            separation_ok = getattr(_ex, "separation_ok", None)
            separation_rel = getattr(_ex, "separation_rel", None)
        if _help.action == "BOOST" and _ex is not None:
            if getattr(_ex, "path", "") in ("ruptura", "atrapado"):
                entry_mode = "SPIKE"
                is_spike = True
                wyckoff_event = "spring" if direction == "CALL" else "upthrust"
                exhaustion_candle = getattr(_ex, "exhaustion_candle", None)
                # MODO OBSERVACIÓN (Ruben 2026-07-26): si está ON, registramos
                # el desglose de las 6 condiciones del spec en la caja negra PERO
                # NO OPERAMOS (has_signal=False). Sirve para medir con datos reales
                # la frecuencia de disparo del setup antes de activarlo en vivo.
                if STRAT_F_SPIKE_OBSERVE:
                    spike_observe = {
                        "R2_zona_franja": bool(getattr(_ex, "in_extreme_zone", False)),
                        "R2bis_separacion_abierta": getattr(_ex, "separation_ok", None),
                        "cruce_m15_confirmado": bool(getattr(_ex, "cross_confirmed", False)),
                        "R3_m5_alineado": getattr(_ex, "m5_aligned", None),
                        "R3bis_m5_agotado": getattr(_ex, "m5_exhausted", None),
                        "R4_rechazo_o_atrapado": getattr(_ex, "path", "") in ("ruptura", "atrapado"),
                        "razon": getattr(_ex, "reason", ""),
                        "path": getattr(_ex, "path", None),
                        "separation_rel": getattr(_ex, "separation_rel", None),
                    }
                    return StratFEvaluation(
                        has_signal=False,           # NO opera en modo observación
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
                        wyckoff_event=wyckoff_event,
                        exhaustion_candle=exhaustion_candle,
                        separation_ok=separation_ok,
                        separation_rel=separation_rel,
                        decision="OBSERVE",
                        spike_observe=spike_observe,
                        early_alert=ea_dict,
                        info=f"STRAT-F OBSERVE {direction} banda={band:.5f} ctx={ctx} mode={entry_mode}{_mq_info}",
                    )

    res = StratFEvaluation(
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
        wyckoff_event=wyckoff_event,
        exhaustion_candle=exhaustion_candle,
        separation_ok=separation_ok,
        separation_rel=separation_rel,
        ob_cross_idx=(
            _require_ob_cross(
                (stoch_m15 or {}).get("k_vals") or [],
                (stoch_m15 or {}).get("d_vals") or [],
                direction,
            )
            if not _use_freno
            else None
        ),
        ob_cross_ago=None,
        stoch_k_last=((stoch_m15 or {}).get("k") if isinstance(stoch_m15, dict) else None),
        stoch_d_last=((stoch_m15 or {}).get("d") if isinstance(stoch_m15, dict) else None),
        info=f"STRAT-F {direction} banda={band:.5f} ctx={ctx} mode={entry_mode}{_mq_info}",
    )
    classic_cross_idx = (
        _require_ob_cross(
            (stoch_m15 or {}).get("k_vals") or [],
            (stoch_m15 or {}).get("d_vals") or [],
            direction,
        )
        if _use_freno is False
        else None
    )
    res.ob_cross_idx = classic_cross_idx
    if res.has_signal and classic_cross_idx is not None:
        _classic_ts = getattr(candles_15m[-1], "ts", 0.0)
        StochCrossState.get().register_cross(
            asset=sym or "",
            direction=direction,
            idx=classic_cross_idx,
            k_last=res.stoch_k_last,
            d_last=res.stoch_d_last,
            ts=str(_classic_ts) if _classic_ts is not None else None,
        )
    return res


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
