"""ZONE STRENGTH — reemplazo completo de la evaluación media de S/R.

REEMPLAZA la lógica "media" (zone_ia win_rate aislado + _score_bounce por mecha
+ _score_extreme_direction) por un modelo FÍSICO del soporte/resistencia como una
"línea imaginaria" con un % de FUERZA medible.

FÍSICA (ley de Hooke / conservación del momento en el choque precio↔nivel):
  El precio llega al nivel con una VELOCIDAD de impacto (pendiente de la pierna
  que lo tocó). El nivel opone una RESISTENCIA (grosor de la línea). Cuanto más
  empuja el precio contra la línea (velocidad de llegada + ticks/order-flow al
  tocar) y más sólida sea la línea (cuántas veces rebotó ahí, cuánto tiempo
  aguantó, cuántos ticks la defendieron), MAYOR es la fuerza del rebote.

  %_fuerza = grosor_linea * (1 - |velocidad_impacto|_normalizada)

GROSOR DE LA LÍNEA (recomendación 2026-07-25 — Ruben):
  El grosor PRINCIPAL se calcula de la EFICACIA ESTRUCTURAL REAL del nivel sobre
  3 días de velas M15 cacheadas en el HTFScanner (compute_support_efficacy):
  cuántas veces el precio tocó el nivel y cuántas de esas veces "aguantó"
  (rebote que no rompió en N velas). Es inmediato, no necesita historial de
  operaciones, y es lo que mide "si un soporte es lo suficientemente fuerte
  para que un rebote aguante 15 min".
  Experience Memory (memoria única) queda como REFUERZO SECUNDARIO cuando hay
  suficientes trades cerrados en el nivel.

CONTRATO (RZ7): este módulo es un EVALUADOR. No escribe memoria. Solo lee.
Bandera ZONE_STRENGTH_ENABLED en config.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from config import ZONE_STRENGTH_ENABLED  # type: ignore
except Exception:
    ZONE_STRENGTH_ENABLED = True

# Pesos del grosor de la línea (suman 1.0)
W_EFFICACY = 0.65   # eficacia estructural real de 3 días M15 (componente principal)
W_MEMORY = 0.20     # refuerzo de Experience Memory (trades cerrados en el nivel)
W_TICKS = 0.15      # order-flow real: ticks que defendieron el nivel hoy

# Normalización de eficacia estructural
HOLD_CANDLES_FOR_BOUNCE = 1   # velas tras el toque que cuentan como "aguantó"
EFFICACY_SATURATION = 0.85    # bounce_rate que ya satura el grosor
TOUCHES_SATURATION = 12        # nº de toques que ya satura el grosor
TICKS_SATURATION = 60          # ticks en la vela de rechazo que saturan el grosor
ANGLE_SATURATION_DEG = 25.0    # pendiente de pierna que satura la velocidad

# % de fuerza mínimo para considerar el rebote "suficiente" (gate de aceptación)
MIN_REBOUND_STRENGTH = 0.50

# Grosor mínimo de línea para no ser "línea inexistente" (ruido)
MIN_LINE_THICKNESS = 0.20


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _norm(v: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return _clamp((v - lo) / (hi - lo), 0.0, 1.0)


def compute_support_efficacy(
    level: float,
    candles_15m: List[Any],
    direction: str = "CALL",
    band_pct: float = 0.0008,
    hold_candles: int = HOLD_CANDLES_FOR_BOUNCE,
) -> Dict[str, Any]:
    """Eficacia estructural REAL del nivel sobre velas M15 (3 días cacheadas).

    Recorre las velas y cuenta los TOQUES al nivel (low≈level para CALL/soporte,
    high≈level para PUT/resistencia). Por cada toque, mira las `hold_candles`
    siguientes: si el precio se quedó del lado correcto del nivel => "aguantó"
    (rebote válido); si lo rompió => fallo.

    O(velas) — microsegundos sobre 288 velas. No toca red, no toca disco.

    Devuelve:
      touch_count      : nº de toques al nivel
      bounce_count     : nº de toques que aguantaron
      bounce_rate      : bounce_count / touch_count (0..1) — eficacia
      avg_hold_candles: promedio de velas que aguantó antes de romper (o hold_candles)
      last_touch_ago  : velas desde el último toque (recencia)
      efficacy        : bounce_rate normalizado por saturación (0..1)
      detail          : trazabilidad legible
    """
    if not candles_15m or not level:
        return {
            "touch_count": 0, "bounce_count": 0, "bounce_rate": 0.0,
            "avg_hold_candles": 0.0, "last_touch_ago": 9999,
            "efficacy": 0.0, "detail": "sin velas/nivel",
        }
    band = level * band_pct
    n = len(candles_15m)
    touches: List[int] = []  # índices de velas que tocaron el nivel
    for i, c in enumerate(candles_15m):
        if direction == "CALL":  # soporte: low rozó el nivel
            if abs(getattr(c, "low", level) - level) <= band:
                touches.append(i)
        else:  # resistencia: high rozó el nivel
            if abs(getattr(c, "high", level) - level) <= band:
                touches.append(i)

    if not touches:
        return {
            "touch_count": 0, "bounce_count": 0, "bounce_rate": 0.0,
            "avg_hold_candles": 0.0, "last_touch_ago": n,
            "efficacy": 0.0,
            "detail": f"nivel={level:.4f} sin toques en {n} velas M15",
        }

    bounce = 0
    holds = []
    for i in touches:
        # mirar las siguientes `hold_candles` velas
        end = min(n, i + 1 + hold_candles)
        seg = candles_15m[i + 1:end]
        if direction == "CALL":
            # aguantó si ninguna vela cerró por debajo del nivel (rompió soporte)
            broke = any(getattr(s, "close", level) < (level - band) for s in seg)
        else:
            broke = any(getattr(s, "close", level) > (level + band) for s in seg)
        if seg and not broke:
            bounce += 1
            holds.append(len(seg))
        elif seg:
            holds.append(0)

    touch_count = len(touches)
    bounce_count = bounce
    bounce_rate = bounce_count / touch_count if touch_count else 0.0
    avg_hold = (sum(holds) / len(holds)) if holds else 0.0
    last_touch_ago = (n - 1) - touches[-1]

    # eficacia normalizada: bounce_rate y nº de toques ambos importan
    eff_rate = _norm(bounce_rate, 0.0, EFFICACY_SATURATION)
    eff_touch = _norm(touch_count, 1, TOUCHES_SATURATION)
    efficacy = _clamp(0.6 * eff_rate + 0.4 * eff_touch, 0.0, 1.0)

    detail = (
        f"nivel={level:.4f} toques={touch_count} aguantaron={bounce_count} "
        f"rate={bounce_rate:.2f} avg_hold={avg_hold:.1f} "
        f"recencia={last_touch_ago}v -> eficacia={efficacy:.2f}"
    )
    return {
        "touch_count": touch_count, "bounce_count": bounce_count,
        "bounce_rate": round(bounce_rate, 3), "avg_hold_candles": round(avg_hold, 2),
        "last_touch_ago": last_touch_ago, "efficacy": round(efficacy, 3),
        "detail": detail,
    }


def _memory_growth(
    asset: str, direction: str, level: float, mem
) -> Tuple[int, float, float]:
    """REFUERZO SECUNDARIO: trades cerrados en el nivel (Experience Memory).

    Devuelve (n_reacciones, win_rate, avg_hold_sec). Si no hay muestra
    suficiente, devuelve (0, 0.5, 0.0) → no aporta grosor.
    """
    if mem is None or not level:
        return 0, 0.5, 0.0
    try:
        from zone_ia import ZONE_BAND_PCT  # reusa la banda de clustering validada
    except Exception:
        ZONE_BAND_PCT = 0.0015
    band = level * ZONE_BAND_PCT
    try:
        similars = mem.query_similar(
            {"asset": str(asset), "direction": direction}, limit=200
        )
        closed = [e for e in similars if e.is_closed()]
        in_zone = [
            e for e in closed
            if e.evento.get("nivel") is not None
            and abs(e.evento.get("nivel") - level) <= band
        ]
        if len(in_zone) < 3:  # refuerzo, no requiere muestra grande
            return 0, 0.5, 0.0
        wins = sum(1 for e in in_zone if e.resultado.get("decision") == "WIN")
        wr = wins / len(in_zone)
        holds = [
            e.evolucion.get("tiempo_a_invalidacion_s")
            for e in in_zone
            if isinstance(e.evolucion.get("tiempo_a_invalidacion_s"), (int, float))
            and e.evolucion.get("tiempo_a_invalidacion_s") > 0
        ]
        avg_hold = (sum(holds) / len(holds)) if holds else 0.0
        return len(in_zone), wr, avg_hold
    except Exception:
        return 0, 0.5, 0.0


def _get_price(c, key, default):
    """Lee low/high/close de un Candle o de un dict (robusto)."""
    if isinstance(c, dict):
        v = c.get(key)
        return v if v is not None else default
    v = getattr(c, key, None)
    return v if v is not None else default


def _ticks_in_reject_candle(candles: List[Any], level: float, direction: str) -> int:
    """Ticks de la vela que tocó el nivel (order-flow real en el impacto).

    Para CALL en piso: la última vela cuyo low rozó el nivel.
    Para PUT en techo: la última vela cuyo high rozó el nivel.
    Acepta Candle o dict (robusto ante tipos del caller/tests).
    """
    if not candles or not level:
        return 0
    last = candles[-1]
    last_close = _get_price(last, "close", level)
    tol = (last_close or level) * 0.0008
    if direction == "CALL":
        touched = abs(_get_price(last, "low", level) - level) <= tol
    else:
        touched = abs(_get_price(last, "high", level) - level) <= tol
    if touched:
        return int(_get_price(last, "ticks", 0) or 0)
    for c in reversed(candles[-4:-1]):
        if direction == "CALL":
            if abs(_get_price(c, "low", level) - level) <= tol:
                return int(_get_price(c, "ticks", 0) or 0)
        else:
            if abs(_get_price(c, "high", level) - level) <= tol:
                return int(_get_price(c, "ticks", 0) or 0)
    return 0

def _line_thickness(
    efficacy: float,
    n_reactions: int,
    win_rate: float,
    ticks_in_reject: int,
) -> float:
    """Grosor de la línea ∈ [0,1].

    Eficacia estructural (3 días M15) es el componente PRINCIPAL.
    Experience Memory es refuerzo secundario (solo si hay muestra).
    Order-flow (ticks) es el modulador en vivo.
    """
    eff_component = _clamp(efficacy, 0.0, 1.0)

    mem_norm = _norm(n_reactions, 3, 20)
    wr_factor = win_rate if n_reactions >= 3 else 0.5
    mem_component = mem_norm * wr_factor

    ticks_component = _norm(ticks_in_reject, 0.0, TICKS_SATURATION)

    thickness = (
        W_EFFICACY * eff_component
        + W_MEMORY * mem_component
        + W_TICKS * ticks_component
    )
    return _clamp(thickness, 0.0, 1.0)


def _impact_velocity(angle_deg: Optional[float]) -> float:
    """Velocidad de impacto ∈ [0,1] desde el ángulo de la pierna que tocó el nivel.

    |angle| grande = llegó empinado = más velocidad = la línea necesita más fuerza.
    """
    if angle_deg is None:
        return 0.3  # neutral si no hay dato de ángulo
    return _norm(abs(angle_deg), 0.0, ANGLE_SATURATION_DEG)


def compute_rebound_strength(
    *,
    asset: str,
    direction: str,
    level: float,
    candles_15m: Optional[List[Any]] = None,
    candles: Optional[List[Any]] = None,
    math_quality: Optional[Dict[str, Any]] = None,
    mem=None,
) -> Dict[str, Any]:
    """Calcula el % de fuerza del rebote en el nivel.

    Devuelve dict con:
      strength_pct      ∈ [0,1]  → % de fuerza del rebote (tu "línea imaginaria")
      line_thickness    ∈ [0,1]  → grosor de la línea
      impact_velocity   ∈ [0,1]  → velocidad de llegada del precio
      efficacy_*        : eficacia estructural de 3 días M15
      n_reactions, win_rate, ticks_in_reject
      sufficient        bool     → strength_pct >= MIN_REBOUND_STRENGTH
      detail            str      → trazabilidad legible
    """
    if not ZONE_STRENGTH_ENABLED:
        return {
            "strength_pct": 0.5, "line_thickness": 0.5, "impact_velocity": 0.3,
            "n_reactions": 0, "win_rate": 0.5, "ticks_in_reject": 0,
            "efficacy_touch_count": 0, "efficacy_bounce_rate": 0.0,
            "efficacy": 0.0, "sufficient": True,
            "detail": "ZONE_STRENGTH desactivado (neutral)",
        }

    if not level:
        return {
            "strength_pct": 0.0, "line_thickness": 0.0, "impact_velocity": 0.3,
            "n_reactions": 0, "win_rate": 0.5, "ticks_in_reject": 0,
            "efficacy_touch_count": 0, "efficacy_bounce_rate": 0.0,
            "efficacy": 0.0, "sufficient": False,
            "detail": "sin nivel (level=None) => no evaluable",
        }

    c15 = candles_15m or candles or []

    # 1) EFICACIA ESTRUCTURAL REAL (3 días M15) — componente PRINCIPAL
    eff = compute_support_efficacy(level, c15, direction=direction)
    efficacy = eff["efficacy"]

    # 2) REFUERZO SECUNDARIO: Experience Memory (trades cerrados en el nivel)
    n_react, wr, _avg_hold = _memory_growth(asset, direction, level, mem)

    # 3) Order-flow real en el rechazo (ticks de la vela que tocó el nivel)
    ticks_in_reject = _ticks_in_reject_candle(c15, level, direction)

    line_thickness = _line_thickness(efficacy, n_react, wr, ticks_in_reject)

    # 4) Velocidad de impacto desde el ángulo de la pierna (math_quality)
    angle = None
    if isinstance(math_quality, dict):
        angle = math_quality.get("angle_deg")
    impact_vel = _impact_velocity(angle)

    # % de fuerza = grosor * (1 - velocidad). Si la línea es gruesa y el precio
    # llegó despacio → rebote fuerte. Si llegó empinado y la línea es fina → 0.
    strength_pct = _clamp(line_thickness * (1.0 - impact_vel), 0.0, 1.0)

    sufficient = (
        line_thickness >= MIN_LINE_THICKNESS
        and strength_pct >= MIN_REBOUND_STRENGTH
    )

    detail = (
        f"[EFICACIA 3d-M15] {eff['detail']} | "
        f"grosor={line_thickness:.2f} (mem_n={n_react},wr={wr:.2f},"
        f"ticks={ticks_in_reject}) vel_impacto={impact_vel:.2f} (ang={angle}) "
        f"-> fuerza_rebote={strength_pct:.2f}"
    )
    return {
        "strength_pct": round(strength_pct, 3),
        "line_thickness": round(line_thickness, 3),
        "impact_velocity": round(impact_vel, 3),
        "n_reactions": n_react,
        "win_rate": round(wr, 3),
        "ticks_in_reject": ticks_in_reject,
        "efficacy_touch_count": eff["touch_count"],
        "efficacy_bounce_count": eff["bounce_count"],
        "efficacy_bounce_rate": eff["bounce_rate"],
        "efficacy_avg_hold_candles": eff["avg_hold_candles"],
        "efficacy_last_touch_ago": eff["last_touch_ago"],
        "efficacy": efficacy,
        "sufficient": bool(sufficient),
        "detail": detail,
    }


class ZoneStrength:
    """API de clase (compatible con el patrón de ZoneIA)."""

    _mem = None

    @classmethod
    def _memory(cls):
        if cls._mem is None:
            try:
                from experience_engine import ExperienceMemory

                cls._mem = ExperienceMemory()
            except Exception:
                cls._mem = False
        return cls._mem or None

    @classmethod
    def score(cls, entry: Any) -> Dict[str, Any]:
        asset = getattr(entry, "asset", None)
        direction = (getattr(entry, "direction", "") or "").upper()
        if not asset or direction not in ("CALL", "PUT"):
            return {"strength_pct": 0.5, "sufficient": True, "detail": "sin asset/dir"}
        level = getattr(entry, "entry_price", None)
        if not level:
            candles = getattr(entry, "candles", None) or []
            if candles:
                last = candles[-1]
                level = getattr(last, "close", None) or getattr(last, "c", None)
        mq = getattr(entry, "math_quality", None)
        if mq is None:
            sd = getattr(entry, "strategy_details", None)
            if isinstance(sd, dict):
                mq = sd.get("math_quality")
        return compute_rebound_strength(
            asset=asset,
            direction=direction,
            level=level,
            candles_15m=getattr(entry, "candles_15m", None),
            candles=getattr(entry, "candles", None),
            math_quality=mq,
            mem=cls._memory(),
        )
