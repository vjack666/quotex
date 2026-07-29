from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Callable, List, Tuple

from models import (
    Candle,
    ConsolidationZone,
    CandidateEntry,
    SignalMode,
)
from zone_ia import ZoneIA
try:
    from zone_strength import ZoneStrength, compute_rebound_strength  # type: ignore
except Exception:
    ZoneStrength = None
    compute_rebound_strength = None
try:
    from config import ZONE_STRENGTH_ENABLED  # type: ignore
except Exception:
    ZONE_STRENGTH_ENABLED = True

# Feature 29 — Contexto Geométrico M15 (OTC). Cache compartida de swings/S-R
# del día; el scorer la consulta para alimentar el filtro de dirección en el
# extremo (RG4/RG6). Cero reglas: solo métricas que las IAs leen.
try:
    from market_geometry_ctx import GEOMETRY_CACHE  # type: ignore
except Exception:
    GEOMETRY_CACHE = None


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY INTELLIGENCE AGENT (Feature 18) — capa extra de ML sobre el score base
# ─────────────────────────────────────────────────────────────────────────────
try:
    from config import ML_ENABLED, ML_MODEL_PATH  # type: ignore
except Exception:  # config not importable (e.g. isolated test) → ML off
    ML_ENABLED = False
    ML_MODEL_PATH = "data/models/lightgbm_v1.pkl"

# Experience Engine (Feature 27): modo ACTIVO. Al evaluar un candidato, el
# engine distribuye su memoria a la IA (solo LECTURA: query_similar). El
# capturador escribe en la memoria (OBSERVATION_ENABLED); las IAs solo leen.
try:
    from config import OBSERVATION_ENABLED  # type: ignore
except Exception:
    OBSERVATION_ENABLED = False

# IA de Zonas (Feature 28): segunda IA lectora de la memoria única. Reemplaza
# el detector por reglas zone_memory.py. Emite zone_confidence. Bandera activa.
try:
    from config import ZONE_IA_ENABLED  # type: ignore
except Exception:
    ZONE_IA_ENABLED = True

_EXP_MEM = None          # singleton de ExperienceMemory (cache)
_EXP_MEM_TS = 0.0
_EXP_MEM_TTL = 30.0      # recarga cada 30s (la memoria crece en vivo)


def _get_experience_memory():
    """Singleton con cache de ExperienceMemory. Solo lectura (query_similar)."""
    global _EXP_MEM, _EXP_MEM_TS
    import time as _t
    if _EXP_MEM is None or (_t.time() - _EXP_MEM_TS) > _EXP_MEM_TTL:
        try:
            from experience_engine import ExperienceMemory  # type: ignore
            _EXP_MEM = ExperienceMemory()
            _EXP_MEM_TS = _t.time()
        except Exception:
            _EXP_MEM = False
    return _EXP_MEM or None


def _apply_experience_distrib(entry: CandidateEntry) -> None:
    """Feature 27 (T8/T9) — distribución ACTIVA: el engine empuja su memoria a
    la IA de Entradas al evaluar un candidato.

    Solo LEE (query_similar): calcula el win rate observado de experiencias
    similares (mismo asset + direccion + contexto stoch) y lo combina como
    ajuste aditivo leve en el score_breakdown. NUNCA escribe en la memoria.
    Detrás de OBSERVATION_ENABLED. No bloquea ni rompe el bot.
    """
    if not OBSERVATION_ENABLED:
        return
    try:
        mem = _get_experience_memory()
        if mem is None:
            return
        asset = getattr(entry, "asset", None)
        direction = (getattr(entry, "direction", "") or "").upper()
        if not asset or direction not in ("CALL", "PUT"):
            return

        # Perfil grueso: mismo asset + misma direccion
        similars = mem.query_similar(
            {"asset": str(asset), "direction": direction}, limit=200
        )
        # Afinar por contexto stoch (estado), sin reglas duras
        stoch = getattr(entry, "stoch_m15", None) or {}
        stoch_zone = stoch.get("estado") if isinstance(stoch, dict) else None

        closed = [e for e in similars if e.is_closed()]
        if stoch_zone:
            same_ctx = [
                e for e in closed
                if (e.contexto_previo.get("stoch_m15", {}) or {}).get("zone") == stoch_zone
            ]
            if len(same_ctx) >= 5:
                closed = same_ctx

        if len(closed) < 5:
            return  # muestra insuficiente: no ajustamos

        wins = sum(1 for e in closed if e.resultado.get("decision") == "WIN")
        wr = wins / len(closed)

        # Ajuste leve (±8 pts) centrado en WR=0.5; no toca el umbral de STRAT-F
        adj = round((wr - 0.5) * 16.0, 1)
        entry.score = round(entry.score + adj, 1)
        try:
            entry.score_breakdown["experience_win_rate"] = round(wr, 3)
            entry.score_breakdown["experience_n"] = len(closed)
            entry.score_breakdown["experience_adj"] = adj
        except (AttributeError, TypeError):
            pass
        setattr(entry, "experience_win_rate", wr)
        setattr(entry, "experience_n", len(closed))
    except Exception:  # nosec - la distribución nunca rompe el bot
        pass


def _finalize_scoring(entry: CandidateEntry) -> None:
    """Aplica todas las capas extra (ML + distribución Experience Engine)."""
    _apply_ml_layer(entry)
    _apply_experience_distrib(entry)

_ML_SCORER = None  # lazy singleton


def _get_ml_scorer():
    """Return the shared MLScorer, or None when ML is disabled/unavailable."""
    global _ML_SCORER
    if not ML_ENABLED:
        return None
    if _ML_SCORER is None:
        try:
            from ml_scorer import MLScorer

            _ML_SCORER = MLScorer(model_path=ML_MODEL_PATH)
        except Exception:
            _ML_SCORER = False  # mark as unavailable so we don't retry forever
    return _ML_SCORER or None


def _entry_to_feature_row(entry: CandidateEntry) -> dict:
    """Build an ml_features-compatible row dict from a live CandidateEntry.

    Uses the raw candle snapshots already on the entry (M1 + M15) plus the
    signal context. Stochastic across TFs is read if the scanner attached it
    (``entry.stoch_m15`` etc.); otherwise those features default to 0 and the
    model still predicts.
    """
    from ml_features import extract_features_full

    def _as_dicts(candles):
        out = []
        for c in candles or []:
            if hasattr(c, "__dict__"):
                out.append(c.__dict__)
            else:
                out.append(c)
        return out

    return {
        "asset": getattr(entry, "asset", None),
        "direction": getattr(entry, "direction", None),
        "payout": getattr(entry, "payout", None),
        "duration_sec": getattr(entry, "duration_sec", None),
        "stoch_m15": getattr(entry, "stoch_m15", None),
        "stoch_m5": getattr(entry, "stoch_m5", None),
        "stoch_m1": getattr(entry, "stoch_m1", None),
        "candles_1m": _as_dicts(getattr(entry, "candles", [])),
        "candles_5m": _as_dicts(getattr(entry, "candles_5m", [])),
        "candles_15m": _as_dicts(getattr(entry, "candles_15m", [])),
        "ts": getattr(entry, "_signal_ts_1m", None),
    }


def _apply_ml_layer(entry: CandidateEntry) -> None:
    """Apply the Entry Intelligence Agent as an EXTRA multiplicative layer.

    final = base * (0.7 + 0.3 * confidence). Never replaces the base score;
    if the model is unavailable or predicts None, the base score is kept
    unchanged (clean fallback). Stores the confidence + delta for traceability.
    """
    scorer = _get_ml_scorer()
    if scorer is None:
        return
    try:
        feats = _entry_to_feature_row(entry)
        conf = scorer.predict(feats)
    except Exception:
        return
    if conf is None:
        return
    base = entry.score
    entry.score = round(base * (0.7 + 0.3 * conf), 1)
    try:
        entry.score_breakdown["ml_confidence"] = round(conf, 3)
        entry.score_breakdown["ml_adjust"] = round(entry.score - base, 1)
    except (AttributeError, TypeError):
        pass
    # Store on the entry for downstream logging / DB recording.
    setattr(entry, "ml_confidence", conf)
    setattr(entry, "ml_adjusted_score", entry.score)



# ─────────────────────────────────────────────────────────────────────────────
#  UMBRALES Y PESOS
# ─────────────────────────────────────────────────────────────────────────────

SCORE_THRESHOLD = 73
MAX_ENTRIES_CYCLE = 1

# Pesos para cada modo (suman 100)
WEIGHTS_REBOUND: dict[str, int] = {
    "compression": 20,
    "bounce":      35,
    "trend":       25,
    "payout":      20,
}

WEIGHTS_BREAKOUT: dict[str, int] = {
    "compression": 15,
    "momentum":    35,
    "trend":       30,
    "payout":      20,
}

RANGE_EXCELLENT = 0.0010
RANGE_GOOD      = 0.0015
RANGE_OK        = 0.0020
RANGE_MAX       = 0.0030

BOUNCE_CANDLES = 3
WICK_RATIO_MIN = 0.4

TREND_EMA_FAST = 10
TREND_EMA_SLOW = 20

PAYOUT_MIN = 84
PAYOUT_MAX = 95

# Contexto histórico: niveles swing en H1 (cubre ~3 días con 80 velas)
HIST_LEVEL_TOUCH_PCT   = 0.0015  # 0.15% — proximidad para considerar "en el nivel"
HIST_LEVEL_SWING_N     = 3       # velas a cada lado para confirmar pivote swing
HIST_LEVEL_PUT_BONUS   = 18.0    # bonus PUT cuando precio choca con alto histórico
HIST_LEVEL_CALL_BONUS  = 12.0    # bonus CALL cuando precio choca con bajo histórico
HIST_LEVEL_PENALTY     = 12.0    # penalización si operamos contra el nivel histórico

# Ajuste por antigüedad de zona (minutos → puntos: negativos penalizan, positivos bonifican)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS (unificados en math_utils)
# ─────────────────────────────────────────────────────────────────────────────

from math_utils import clamp, ema, normalize


# ─────────────────────────────────────────────────────────────────────────────
#  COMPONENTES COMPARTIDOS
# ─────────────────────────────────────────────────────────────────────────────

def _score_compression(zone: ConsolidationZone, weight: int) -> float:
    r = zone.range_pct

    if r <= RANGE_EXCELLENT:
        ratio = 1.0
    elif r <= RANGE_GOOD:
        ratio = 0.85 + 0.15 * (RANGE_GOOD - r) / (RANGE_GOOD - RANGE_EXCELLENT)
    elif r <= RANGE_OK:
        ratio = 0.60 + 0.25 * (RANGE_OK - r) / (RANGE_OK - RANGE_GOOD)
    elif r <= RANGE_MAX:
        ratio = 0.0 + 0.60 * (RANGE_MAX - r) / (RANGE_MAX - RANGE_OK)
    else:
        ratio = 0.0

    bars_bonus = normalize(zone.bars_inside, 15, 30) * 0.15
    ratio = clamp(ratio + bars_bonus, 0.0, 1.0)

    return round(ratio * weight, 2)


def _score_payout(payout: int, weight: int) -> float:
    ratio = normalize(payout, PAYOUT_MIN, PAYOUT_MAX)
    return round(ratio * weight, 2)


def _score_trend(candles: List[Candle], direction: str, weight: int) -> float:
    needed = TREND_EMA_SLOW + 5
    if len(candles) < needed:
        return weight * 0.5

    closes = [c.close for c in candles[-40:]]
    ema_fast = ema(closes, TREND_EMA_FAST)
    ema_slow = ema(closes, TREND_EMA_SLOW)

    if not ema_fast or not ema_slow:
        return weight * 0.5

    ef_last = ema_fast[-1]
    es_last = ema_slow[-1]

    if len(ema_fast) >= 5:
        slope = (ema_fast[-1] - ema_fast[-5]) / (ema_fast[-5] or 1)
    else:
        slope = 0.0

    if direction == "put":
        aligned = ef_last < es_last
        slope_support = slope < 0
    else:
        aligned = ef_last > es_last
        slope_support = slope > 0

    if aligned and slope_support:
        ratio = 0.85 + 0.15 * normalize(abs(slope) * 100, 0, 0.5)
    elif aligned and not slope_support:
        ratio = 0.55
    elif not aligned and slope_support:
        ratio = 0.35
    else:
        ratio = 0.10

    price = closes[-1]
    if direction == "put" and price < ef_last:
        ratio = clamp(ratio + 0.10, 0.0, 1.0)
    elif direction == "call" and price > ef_last:
        ratio = clamp(ratio + 0.10, 0.0, 1.0)

    return round(ratio * weight, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  COMPONENTES ESPECÍFICOS POR MODO
# ─────────────────────────────────────────────────────────────────────────────

def _score_bounce(candles: List[Candle], zone: ConsolidationZone, direction: str, weight: int) -> float:
    """Componente REBOUND: mide calidad de mecha en el extremo y momentum de velas recientes."""
    if len(candles) < BOUNCE_CANDLES + 1:
        return 0.0

    last = candles[-1]
    total_range = last.high - last.low
    if total_range == 0:
        wick_score = 0.0
    elif direction == "put":
        upper_wick = last.high - max(last.open, last.close)
        wick_score = normalize(upper_wick / total_range, WICK_RATIO_MIN, 0.8)
    else:
        lower_wick = min(last.open, last.close) - last.low
        wick_score = normalize(lower_wick / total_range, WICK_RATIO_MIN, 0.8)

    recent = candles[-(BOUNCE_CANDLES + 1):]
    if direction == "put":
        bearish = sum(1 for c in recent if c.close < c.open)
        momentum_score = bearish / len(recent)
    else:
        bullish = sum(1 for c in recent if c.close > c.open)
        momentum_score = bullish / len(recent)

    combined = 0.6 * wick_score + 0.4 * momentum_score
    return round(combined * weight, 2)


def _score_momentum(candles: List[Candle], weight: int) -> float:
    """
    Componente BREAKOUT: mide fuerza de la vela de ruptura vs historial.
    Interpolado linealmente: cuerpo = 1.0× avg → 0 pts; cuerpo = 2.5× avg → 100 pts.
    """
    if len(candles) < 2:
        return 0.0

    breakout_candle = candles[-1]
    lookback = candles[-(11):-1] if len(candles) >= 11 else candles[:-1]
    if not lookback:
        return round(weight * 0.5, 2)

    avg = mean(c.body for c in lookback) or 0.0
    if avg == 0:
        return round(weight * 0.5, 2)

    ratio = breakout_candle.body / avg  # 1.0x a 2.5x
    normalized = normalize(ratio, 1.0, 2.5)
    return round(normalized * weight, 2)


def _age_adjustment(zone: ConsolidationZone) -> float:
    """Ajuste por antigüedad de zona. Negativo penaliza, positivo bonifica."""
    age = zone.age_minutes
    if age < 10.0:
        return -12.0
    if age < 30.0:
        return -5.0
    if age <= 90.0:
        return 0.0
    return 5.0


def detect_swing_levels(
    candles_h1: List[Candle],
    n: int = HIST_LEVEL_SWING_N,
) -> tuple[List[float], List[float]]:
    """Detecta pivotes swing high/low en velas H1 para contexto histórico."""
    highs: List[float] = []
    lows: List[float] = []
    if len(candles_h1) < 2 * n + 1:
        return highs, lows

    for index in range(n, len(candles_h1) - n):
        candle = candles_h1[index]
        left = candles_h1[index - n:index]
        right = candles_h1[index + 1:index + n + 1]
        if all(candle.high >= item.high for item in left) and all(candle.high >= item.high for item in right):
            highs.append(candle.high)
        if all(candle.low <= item.low for item in left) and all(candle.low <= item.low for item in right):
            lows.append(candle.low)
    return highs, lows


def _score_historical_level(entry: CandidateEntry) -> float:
    """Ajuste por cercanía a soportes/resistencias históricas detectadas en H1."""
    if not entry.candles_h1:
        return 0.0

    price = float(entry.candles[-1].close) if entry.candles else float(entry.candles_h1[-1].close)
    swing_highs, swing_lows = detect_swing_levels(entry.candles_h1)
    if not swing_highs and not swing_lows:
        return 0.0

    tolerance = price * HIST_LEVEL_TOUCH_PCT
    near_high = any(abs(price - level) <= tolerance for level in swing_highs)
    near_low = any(abs(price - level) <= tolerance for level in swing_lows)

    if near_high:
        return HIST_LEVEL_PUT_BONUS if entry.direction == "put" else -HIST_LEVEL_PENALTY
    if near_low:
        return HIST_LEVEL_CALL_BONUS if entry.direction == "call" else -HIST_LEVEL_PENALTY
    return 0.0

try:
    from config import MARKET_GEOMETRY_ENABLED  # type: ignore
except Exception:
    MARKET_GEOMETRY_ENABLED = False

# Feature 29 / RG6 — confirmación por CUERPO en el extremo del rango.
# Lección EURJPY 2247864af2e7b77e: la mecha tocó el piso pero el CUERPO cerró
# alcista → PUT perdió. El filtro correcto NO es "prohibido entrar en el
# extremo", sino distinguir spike con convicción (cuerpo a favor, sin mecha
# opuesta) de rebote (mecha toca el nivel, cuerpo cierra en contra).
EXTREME_TOUCH_PCT      = 0.0015  # proximidad al extremo para activar el filtro
EXTREME_BODY_MIN_PCT   = 0.40    # cuerpo mínimo (|c-o|/rango) para "convicción"
EXTREME_DIR_PENALTY    = -8.0    # ajuste aditivo leve si el cuerpo NO confirma


def _score_extreme_direction(entry: CandidateEntry, geom=None) -> float:
    """Feature 29 (RG6) — dirección en el extremo del rango/swing.

    Si el precio está en un extremo (piso/techo de entry.zone o swing de
    geometría) y la vela de entrada NO tiene cuerpo a favor de la dirección
    (cuerpo decidido + cierre en la mitad correcta del rango de la vela),
    penaliza levemente (-8pt). Sin extremo o sin datos → 0.0 (neutral).
    """
    if not MARKET_GEOMETRY_ENABLED or not entry.candles:
        return 0.0

    candle = entry.candles[-1]
    price = float(candle.close)
    tol = price * EXTREME_TOUCH_PCT

    # Extremos: zona (piso/techo) y/o swings de geometría externa
    levels_low: List[float] = []
    levels_high: List[float] = []
    if entry.zone is not None:
        levels_low.append(float(entry.zone.floor))
        levels_high.append(float(entry.zone.ceiling))
    if geom is not None:
        levels_high.extend(float(x) for x in getattr(geom, "swing_highs", []) or [])
        levels_low.extend(float(x) for x in getattr(geom, "swing_lows", []) or [])
    if not levels_low and not levels_high:
        return 0.0

    lo, hi = float(candle.low), float(candle.high)
    at_floor = any(abs(lo - lvl) <= tol for lvl in levels_low)
    at_ceiling = any(abs(hi - lvl) <= tol for lvl in levels_high)

    direction = entry.direction.lower()
    if not ((direction == "put" and at_floor) or (direction == "call" and at_ceiling)):
        return 0.0  # no estamos vendiendo en piso ni comprando en techo

    rng = hi - lo
    if rng <= 0:
        return 0.0
    body_pct = abs(candle.close - candle.open) / rng
    close_pos = (candle.close - lo) / rng  # 0 = low, 1 = high

    if direction == "put":
        confirmed = (candle.close < candle.open
                     and body_pct >= EXTREME_BODY_MIN_PCT
                     and close_pos <= 0.5)
    else:
        confirmed = (candle.close > candle.open
                     and body_pct >= EXTREME_BODY_MIN_PCT
                     and close_pos >= 0.5)

    if confirmed:
        return 0.0  # spike con convicción: no penalizar
    setattr(entry, "extreme_body_pct", round(body_pct, 3))  # trazabilidad
    return EXTREME_DIR_PENALTY


def _score_zone_ia(entry: CandidateEntry) -> float:
    """Feature 28 — ajuste por zona de reacción descubierta por la IA de Zonas.

    Lee la memoria única (ZoneIA.score) y emite zone_confidence ∈ [0,1].
    Mapea a ajuste aditivo leve (±8 pts) centrado en 0.5. Sin reglas: la zona
    y su fortaleza son salida de la IA, no del capturador. Retorna 0.0 si la IA
    está off o no hay muestra suficiente (neutral).
    """
    conf = ZoneIA.score(entry)
    if conf is None:
        return 0.0
    entry.zone_confidence = conf
    entry.score_breakdown["zone_confidence"] = round(conf, 3)
    return round((conf - 0.5) * 16.0, 1)

# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL DE SCORING
# ─────────────────────────────────────────────────────────────────────────────

def score_candidate(
    entry: CandidateEntry,
    mode: SignalMode | None = None,
) -> float:
    """
    Calcula el score del candidato usando los pesos del modo activo.

    Si `mode` no se pasa explícitamente, se usa `entry.mode`.
    El score se almacena en `entry.score` y el desglose en `entry.score_breakdown`.
    """
    effective_mode = mode if mode is not None else entry.mode
    entry.mode = effective_mode

    # Feature 29 (RG4/RG6): contexto geométrico M15 del día (cache por barra).
    # Lo consulta el filtro de dirección en el extremo. Solo métricas; la IA
    # decide. Sin reglas.
    geom = None
    _c15 = getattr(entry, "candles_15m", None)
    if GEOMETRY_CACHE is not None and _c15:
        try:
            geom = GEOMETRY_CACHE.get(entry.asset, _c15)
        except Exception:
            geom = None
    entry.geometry = geom
    # ── STRAT-F (Fractal / Wyckoff) ────────────────────────────────────────
    # REEMPLAZO COMPLETO de la evaluación media de S/R (2026-07-25): el score
    # refleja el % de FUERZA de la "línea imaginaria" (modelo físico de
    # zone_strength). Si la línea no es suficientemente fuerte para que el
    # rebote aguante, el candidato se DESCALIFICA (score 0 + reject_reason).
    if getattr(entry, "_strategy_origin", None) == "STRAT-F":
        s_payout = float(entry.score_breakdown.get("payout", 0.0))
        age_adj = _age_adjustment(entry.zone) if entry.zone is not None else 0.0

        st = None
        if ZONE_STRENGTH_ENABLED and ZoneStrength is not None:
            st = ZoneStrength.score(entry)
        if st is None:
            st = {"strength_pct": 0.5, "line_thickness": 0.5,
                  "impact_velocity": 0.3, "sufficient": True,
                  "n_reactions": 0, "win_rate": 0.5, "ticks_in_reject": 0,
                  "efficacy_touch_count": 0, "efficacy_bounce_rate": 0.0,
                  "efficacy": 0.0, "detail": "ZoneStrength off"}

        # Score base = fuerza de la línea (0..1) * 80, igual que antes con
        # strength, pero ahora es MEDIBLE (no heurística de fractales).
        s_base = st["strength_pct"] * 80.0
        entry.score_breakdown = {
            "strength_score": round(s_base, 1),
            "payout": round(s_payout, 1),
            "age_adjustment": round(age_adj, 1),
            "line_thickness": st["line_thickness"],
            "impact_velocity": st["impact_velocity"],
            "rebound_strength_pct": st["strength_pct"],
            "efficacy_touch_count": st["efficacy_touch_count"],
            "efficacy_bounce_rate": st["efficacy_bounce_rate"],
            "efficacy": st["efficacy"],
        }
        if not st["sufficient"]:
            # Línea insuficiente: el rebote no aguantaría → rechazo duro.
            entry.score = 0.0
            try:
                setattr(entry, "reject_reason", "WEAK_LINE_STRENGTH")
                entry.score_breakdown["reject_reason"] = "WEAK_LINE_STRENGTH"
                entry.score_breakdown["line_detail"] = st["detail"]
            except (AttributeError, TypeError):
                pass
            _finalize_scoring(entry)
            return entry.score

        total = s_base + s_payout + age_adj
        entry.score = round(total, 1)
        _finalize_scoring(entry)
        return entry.score

    if effective_mode == SignalMode.BREAKOUT:
        w = WEIGHTS_BREAKOUT
        s_comp     = _score_compression(entry.zone, w["compression"])
        s_momentum = _score_momentum(entry.candles, w["momentum"])
        trend_candles = (
            entry.candles_15m
            if len(entry.candles_15m) >= 25
            else entry.candles
        )
        s_trend    = _score_trend(trend_candles, entry.direction, w["trend"])
        s_payout   = _score_payout(entry.payout, w["payout"])
        age_adj    = _age_adjustment(entry.zone)
        hist_adj   = _score_historical_level(entry)
        zm_adj     = _score_zone_ia(entry)
        ext_adj    = _score_extreme_direction(entry, geom)

        total = s_comp + s_momentum + s_trend + s_payout + age_adj + hist_adj + zm_adj + ext_adj
        entry.score = round(total, 1)
        entry.score_breakdown = {
            "compression": s_comp,
            "momentum":    s_momentum,
            "trend":       s_trend,
            "payout":      s_payout,
            "age_adjustment": age_adj,
            # alias para compatibilidad con código que lee "bounce"
            "bounce":      s_momentum,
        }
        if ext_adj != 0.0:
            entry.score_breakdown["extreme_direction"] = round(ext_adj, 1)
        if hist_adj != 0.0:
            entry.score_breakdown["hist_level"] = round(hist_adj, 1)
        if zm_adj != 0.0:
            entry.score_breakdown["zone_confidence_adj"] = round(zm_adj, 1)
        if entry.zone_confidence is not None:
            entry.score_breakdown["zone_confidence"] = round(entry.zone_confidence, 3)
    else:
        w = WEIGHTS_REBOUND
        s_comp    = _score_compression(entry.zone, w["compression"])
        # REEMPLAZO (2026-07-25): el componente REBOTE ya no usa _score_bounce
        # (mecha burda) ni extreme_direction ni zone_confidence aislado. Usa el
        # % de fuerza de la línea (ZoneStrength) como medida real del rebote.
        s_bounce = 0.0
        st = None
        if ZONE_STRENGTH_ENABLED and ZoneStrength is not None:
            st = ZoneStrength.score(entry)
        if st is not None:
            s_bounce = st["strength_pct"] * w["bounce"]  # fuerza de línea → pts de rebote
        trend_candles = (
            entry.candles_15m
            if len(entry.candles_15m) >= 25
            else entry.candles
        )
        s_trend   = _score_trend(trend_candles, entry.direction, w["trend"])
        s_payout  = _score_payout(entry.payout, w["payout"])
        age_adj   = _age_adjustment(entry.zone)
        hist_adj  = _score_historical_level(entry)
        zm_adj    = _score_zone_ia(entry)
        ext_adj    = _score_extreme_direction(entry, geom)

        total = s_comp + s_bounce + s_trend + s_payout + age_adj + hist_adj + zm_adj + ext_adj
        entry.score = round(total, 1)
        entry.score_breakdown = {
            "compression": s_comp,
            "bounce":      round(s_bounce, 1),
            "trend":       s_trend,
            "payout":      s_payout,
            "age_adjustment": age_adj,
            "rebound_strength_pct": st["strength_pct"] if st else None,
            "line_thickness": st["line_thickness"] if st else None,
            "impact_velocity": st["impact_velocity"] if st else None,
        }
        if st is not None:
            entry.score_breakdown["line_detail"] = st["detail"]
        if ext_adj != 0.0:
            entry.score_breakdown["extreme_direction"] = round(ext_adj, 1)
        if hist_adj != 0.0:
            entry.score_breakdown["hist_level"] = round(hist_adj, 1)
        if zm_adj != 0.0:
            entry.score_breakdown["zone_confidence_adj"] = round(zm_adj, 1)
        if entry.zone_confidence is not None:
            entry.score_breakdown["zone_confidence"] = round(entry.zone_confidence, 3)

    _finalize_scoring(entry)
    return entry.score


def select_best(
    candidates: List[CandidateEntry],
    max_entries: int = MAX_ENTRIES_CYCLE,
    threshold: int = SCORE_THRESHOLD,
    *,
    threshold_for: Callable[[CandidateEntry], int] | None = None,
) -> Tuple[List[CandidateEntry], List[CandidateEntry]]:
    def _thresh(c: CandidateEntry) -> int:
        if threshold_for is not None:
            return threshold_for(c)
        return threshold

    passed = [c for c in candidates if c.score >= _thresh(c)]
    failed = [c for c in candidates if c.score < _thresh(c)]

    passed.sort(key=lambda x: -x.score)
    failed.sort(key=lambda x: -x.score)

    selected = passed[:max_entries]
    rejected = passed[max_entries:] + failed

    return selected, rejected


def explain_score(entry: CandidateEntry, threshold: int = SCORE_THRESHOLD) -> str:
    bd = entry.score_breakdown
    mode_label = entry.mode.value.upper()
    age_adjustment = bd.get("age_adjustment", 0.0)
    age_txt = f" (ajuste antigüedad zona: {age_adjustment:+.1f})" if age_adjustment != 0 else ""
    hist_adj = bd.get("hist_level", 0.0)
    hist_txt = ""
    if hist_adj > 0:
        hist_txt = f" | nivel histórico {hist_adj:+.1f}"
    elif hist_adj < 0:
        hist_txt = f" | contra nivel histórico {hist_adj:+.1f}"

    if entry.mode == SignalMode.BREAKOUT:
        w = WEIGHTS_BREAKOUT
        lines = [
            f"+- SCORE BREAKDOWN [{mode_label}]: {entry.asset} ({entry.direction.upper()}) -",
            f"| Score total   : {entry.score:5.1f} / 100  {'OK' if entry.score >= threshold else 'SKIP'}{age_txt}{hist_txt}",
            f"| Min threshold : {threshold}",
            f"| S1 Compresión : {bd.get('compression', 0):5.1f} / {w['compression']} (range={entry.zone.range_pct*100:.3f}% bars={entry.zone.bars_inside})",
            f"| S2 Momentum   : {bd.get('momentum', 0):5.1f} / {w['momentum']}",
            f"| S3 Tendencia  : {bd.get('trend', 0):5.1f} / {w['trend']}",
            f"| S4 Payout     : {bd.get('payout', 0):5.1f} / {w['payout']} (payout={entry.payout}%)",
            f"| Zona edad     : {entry.zone.age_minutes:.0f} min → ajuste {age_adjustment:+.1f} pts",
            f"| Nivel H1      : ajuste {hist_adj:+.1f} pts",
            "+--------------------------------------------",
        ]
    else:
        w = WEIGHTS_REBOUND
        lines = [
            f"+- SCORE BREAKDOWN [{mode_label}]: {entry.asset} ({entry.direction.upper()}) -",
            f"| Score total   : {entry.score:5.1f} / 100  {'OK' if entry.score >= threshold else 'SKIP'}{age_txt}{hist_txt}",
            f"| Min threshold : {threshold}",
            f"| S1 Compresión : {bd.get('compression', 0):5.1f} / {w['compression']} (range={entry.zone.range_pct*100:.3f}% bars={entry.zone.bars_inside})",
            f"| S2 Rebote     : {bd.get('bounce', 0):5.1f} / {w['bounce']}",
            f"| S3 Tendencia  : {bd.get('trend', 0):5.1f} / {w['trend']}",
            f"| S4 Payout     : {bd.get('payout', 0):5.1f} / {w['payout']} (payout={entry.payout}%)",
            f"| Zona edad     : {entry.zone.age_minutes:.0f} min → ajuste {age_adjustment:+.1f} pts",
            f"| Nivel H1      : ajuste {hist_adj:+.1f} pts",
            "+--------------------------------------------",
        ]
    return "\n".join(lines)
