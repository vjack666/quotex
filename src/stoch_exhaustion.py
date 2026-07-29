"""Agotamiento verdadero del estocástico M15 para STRAT-F — ZONA ADAPTATIVA.

Actualizacion COMPLETA del criterio de entrada en zonas extremas (Z1/Z5).
Reemplaza la logica de "BOOST ciego apenas el %K toca el extremo" por una
regla de agotamiento CONFIRMADO que exige:

  1. ZONA ADAPTATIVA: el rango de precio reciente del par (NO pips fijos).
     El precio debe estar en el extremo (sobreventa/sobrecompra) y, para
     confirmar, hay DOS caminos validos:
       (A) RUPTURA: el precio SALIO de la zona y la vela de agotamiento
           toca la franja de la zona (soporte/resistencia).
       (B) ATRAPADO: el estocastico LLEVA varias velas EN el extremo
           (0-20 / 80-100) SIN acercarse a salir de la linea 20/80 — es
           decir, el %K nunca cruzo de vuelta al centro. Eso es
           agotamiento en el extremo, no una falsa reversión.
  2. CRUCE CONFIRMADO: %K/%D cruzaron en la direccion del rebote con
     >=1 vela M15 de antiguedad (>=5 min).
  3. VELA DE AGOTAMIENTO: en/cerca de la franja de la zona debe haber
     vela de rechazo — martillo, doji (indecision) o estrella fugaz.

Esto es PURO (no toca I/O). Funciona para CUALQUIER par: si no se pasa
zone_lo/zone_hi, se calculan adaptativamente del rango reciente (% precio).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence

from models import Candle

Direction = Literal["CALL", "PUT"]
Action = Literal["EXHAUST_CONFIRMED", "EXHAUST_WAIT"]


@dataclass(frozen=True)
class ExhaustResult:
    action: Action
    reason: str
    # diagnostico (backbox / auditoria)
    in_extreme_zone: bool = False
    cross_confirmed: bool = False
    cross_ago: Optional[int] = None
    exhaustion_candle: Optional[str] = None
    at_support_resistance: bool = False
    path: Optional[str] = None  # "ruptura" | "atrapado" | None
    # R2-bis (spec strat_f_spike_wyckoff_phase_a): separacion %K/%D del cruce.
    separation_ok: Optional[bool] = None    # None = sin datos para medir (no bloquea)
    separation_rel: Optional[float] = None  # |K-D| actual / rango reciente de |K-D|
    # R3 (spec): M5 alineado con la direccion de entrada.
    m5_aligned: Optional[bool] = None       # None = sin datos M5 para decidir
    # R3-bis (spec): M5 agotado en SU propio extremo (k<20 CALL / k>80 PUT).
    m5_exhausted: Optional[bool] = None


# --- deteccion de vela de agotamiento (puro, sobre OHLC) -----------------


def _candle_metrics(c: Candle) -> tuple[float, float, float, float, float, float, float]:
    """(open, high, low, close, cuerpo, mecha_sup, mecha_inf)."""
    o, h, l, cl = float(c.open), float(c.high), float(c.low), float(c.close)
    cuerpo = abs(cl - o)
    mecha_sup = h - max(o, cl)
    mecha_inf = min(o, cl) - l
    return o, h, l, cl, cuerpo, mecha_sup, mecha_inf


def classify_exhaustion_candle(
    c: Candle,
    direction: str,
    body_ratio: float = 0.35,
    wick_ratio: float = 0.55,
) -> Optional[str]:
    """Detecta vela de agotamiento en la franja S/R.

    direction = lado del rebote esperado:
      CALL (rebote en soporte)  -> mecha INFERIOR larga o doji.
      PUT  (rebote en resist.)  -> mecha SUPERIOR larga o doji.
    Prioridad: martillo/estrellafugaz (mecha direccional) antes que doji.
    Devuelve 'martillo' | 'doji' | 'estrellafugaz' | None.
    """
    o, h, l, cl, cuerpo, mecha_sup, mecha_inf = _candle_metrics(c)
    rango = (h - l) or 1e-9
    if cuerpo / rango > body_ratio:
        return None  # vela de tendencia, no agotamiento
    if direction == "CALL":
        if mecha_inf / rango >= 0.80 and mecha_sup / rango <= 0.25:
            return "estrellafugaz"
        if mecha_inf / rango >= wick_ratio and mecha_sup / rango <= 0.30:
            return "martillo"
    else:  # PUT
        if mecha_sup / rango >= 0.80 and mecha_inf / rango <= 0.25:
            return "estrellafugaz"
        if mecha_sup / rango >= wick_ratio and mecha_inf / rango <= 0.30:
            return "martillo"
    if (mecha_sup / rango >= 0.30 and mecha_inf / rango >= 0.30
            and cuerpo / rango <= 0.20):
        return "doji"
    return None


# --- cruce confirmado (>=1 vela de antiguedad) ---------------------------


def _cross_ago(k_vals: List[float], d_vals: List[float], direction: str) -> Optional[int]:
    """Velas M15 desde el ULTIMO cruce %K/%D en la direccion del rebote.
    CALL=alcista (K subio sobre D). PUT=bajista (K bajo bajo D)."""
    if len(k_vals) < 2 or len(d_vals) < 2:
        return None
    cross_idx: Optional[int] = None
    n = min(len(k_vals), len(d_vals))  # %D suele ser mas corta que %K
    for i in range(1, n):
        k0, d0, k1, d1 = k_vals[i - 1], d_vals[i - 1], k_vals[i], d_vals[i]
        if direction == "CALL":
            if k0 <= d0 and k1 > d1:
                cross_idx = i
        else:  # PUT
            if k0 >= d0 and k1 < d1:
                cross_idx = i
    if cross_idx is None:
        return None
    return len(k_vals) - 1 - cross_idx


def _cross_separation(
    k_vals: List[float],
    d_vals: List[float],
    *,
    sep_lookback: int = 14,
    sep_min_frac: float = 0.35,
) -> tuple[Optional[bool], Optional[float]]:
    """R2-bis: separacion ADAPTATIVA entre %K y %D tras el cruce.

    La estrategia exige que las lineas salgan de la franja ABIERTAS (la
    separacion se formo antes de salir), filtrando cruces "pegajosos" en el
    borde. La medida es RELATIVA al comportamiento reciente del PROPIO
    oscilador del par: |K-D| actual comparado con el MAXIMO |K-D| de las
    ultimas `sep_lookback` velas. PROHIBIDO un umbral absoluto fijo (nada
    de "3-5 puntos") — doctrina del spec (misma regla que la zona de precio).

    separation_rel = |K-D| actual / max(|K-D| reciente)
    separation_ok  = separation_rel >= sep_min_frac (fraccion del propio rango)

    Devuelve (ok, rel). (None, None) si no hay datos suficientes (no bloquea:
    fail-safe igual que el resto del modulo).
    """
    n = min(len(k_vals), len(d_vals))
    if n < 3:
        return None, None
    diffs = [abs(k_vals[-i] - d_vals[-i]) for i in range(1, min(sep_lookback, n) + 1)]
    ref = max(diffs)
    if ref <= 1e-9:
        # oscilador plano: sin comportamiento reciente que sirva de vara
        return None, None
    rel = diffs[0] / ref
    return rel >= sep_min_frac, round(rel, 4)


def _trapped_in_extreme(
    k_vals: List[float],
    d_vals: List[float],
    direction: str,
    oversold: float,
    overbought: float,
    trap_window: int,
) -> Optional[int]:
    """Detecta estocastico ATASCADO en el extremo sin salir.

    PUT: las ultimas `trap_window` velas tienen k>=overbought (en sobrecompra)
    y el %K NUNCA baja a <= la linea media (overbought - margen). Es decir,
    muchos cruces adentro de 80-100 pero nunca se acerca a salir de 80.
    Devuelve el numero de velas atrapadas, o None si no aplica.
    """
    if len(k_vals) < trap_window:
        return None
    recent_k = k_vals[-trap_window:]
    recent_d = d_vals[-trap_window:] if len(d_vals) >= trap_window else d_vals
    mid = overbought if direction == "PUT" else oversold
    lo, hi = min(oversold, overbought), max(oversold, overbought)
    if direction == "PUT":
        # todas en sobrecompra y ninguna baja del umbral de salida
        if all(k >= overbought for k in recent_k) and all(k >= mid - (hi - lo) * 0.15 for k in recent_k):
            return len(recent_k)
    else:  # CALL: todas en sobreventa, ninguna sube del umbral de salida
        if all(k <= oversold for k in recent_k) and all(k <= mid + (hi - lo) * 0.15 for k in recent_k):
            return len(recent_k)
    return None


# --- zona adaptativa (sin pips fijos) ------------------------------------


def adaptive_zone(candles: Sequence[Candle], frac: float = 0.5, lookback: int = 40) -> tuple[float, float]:
    """Rango reciente del precio como ZONA. El ancho es `frac` del rango
    total de las ultimas `lookback` velas, centrado en el medio. % del
    precio, NO pips — funciona en cualquier par (AUDUSD o USDPKR)."""
    cs = list(candles[-lookback:])
    if not cs:
        return (0.0, 0.0)
    highs = [float(c.high) for c in cs]
    lows = [float(c.low) for c in cs]
    hi = max(highs)
    lo = min(lows)
    mid = (hi + lo) / 2.0
    half = frac * (hi - lo) / 2.0
    return (mid - half, mid + half)


def _zone_band(zone_lo: float, zone_hi: float) -> float:
    """Banda de tolerancia alrededor de la zona: 30% del ancho de la zona.
    Adaptativa al par, no pips fijos."""
    return max((zone_hi - zone_lo) * 0.3, 1e-9)


# --- API principal --------------------------------------------------------


def _m5_aligned(stoch_m5: dict, direction_u: str) -> Optional[bool]:
    """El M5 debe inclinarse en la direccion de la entrada (regla del usuario).

    PUT exige M5 bajista (k<d o cruce bajista o k bajando).
    CALL exige M5 alcista (k>d o cruce alcista o k subiendo).
    Devuelve True/False; None si no hay datos para decidir (no bloquea).
    """
    k = stoch_m5.get("k")
    d = stoch_m5.get("d")
    cruce = (stoch_m5.get("cruce") or "").lower()
    if k is None and d is None and not cruce:
        return None
    k_dn = k is not None and d is not None and k < d
    k_up = k is not None and d is not None and k > d
    if direction_u == "PUT":
        if cruce == "bajista" or k_dn:
            return True
        if cruce == "alcista" or k_up:
            return False
        return None
    else:  # CALL
        if cruce == "alcista" or k_up:
            return True
        if cruce == "bajista" or k_dn:
            return False
        return None


def _m5_exhausted(stoch_k: Optional[float], direction_u: str) -> bool:
    """R3-bis: M5 agotado en SU propio extremo en el instante de la senal.

    CALL: stoch M5 %K < 20 (sobreventa = el impulso bajista se agoto).
    PUT:  stoch M5 %K > 80 (sobrecompra = el impulso alcista se agoto).
    Separado de _m5_aligned (R3): el M5 puede ir a favor pero ya rebotado
    (no agotado) -> aqui lo detectamos como 'm5_no_exhausted'.
    Sin datos (None) -> False (no bloquea si no hay M5; el caller decide).
    """
    if stoch_k is None:
        return False
    if direction_u == "CALL":
        return stoch_k < 20.0
    if direction_u == "PUT":
        return stoch_k > 80.0
    return False


def evaluate_exhaustion(
    *,
    k: Optional[float],
    d: Optional[float],
    k_vals: Optional[List[float]] = None,
    d_vals: Optional[List[float]] = None,
    direction: str,
    candles_15m: Optional[Sequence[Candle]] = None,
    zone_lo: Optional[float] = None,
    zone_hi: Optional[float] = None,
    stoch_m5: Optional[dict] = None,   # {k,d,estado,cruce} del M5 — DEBE ir en la
                                        # direccion de la entrada (regla del usuario)
    zone_strength: Optional[float] = None,  # % fuerza de la linea imaginaria
                                            # (zone_strength.compute_support_efficacy
                                            # o compute_rebound_strength). FUENTE
                                            # PRINCIPAL de la banda (R7). None ->
                                            # fallback adaptive_zone.
    candles_1m: Optional[Sequence[Candle]] = None,  # ventana M1 de la M15 EN CURSO
                                                     # (intravela, R10). Si se pasa,
                                                     # el camino A busca la vela de
                                                     # rechazo AQUI (no en candles_15m).
    oversold: float = 20.0,
    overbought: float = 80.0,
    cross_min_ago: int = 1,
    lookback: int = 3,
    trap_window: int = 5,       # velas atrapadas en extremo para camino (B)
) -> ExhaustResult:
    """Agotamiento verdadero con ZONA ADAPTATIVA y doble camino de confirmacion.

    Camino A (ruptura): en extremo + cruce confirmado + vela de indecision en
    la franja de la zona.
    Camino B (atrapado): en extremo + cruce confirmado + estocastico atrapado
    varias velas en 0-20/80-100 SIN acercarse a salir de 20/80.

    Sin datos suficientes -> EXHAUST_WAIT (fail-safe).
    """
    direction_u = (direction or "").strip().upper()
    if direction_u not in ("CALL", "PUT"):
        return ExhaustResult("EXHAUST_WAIT", "dir_desconocida")

    if k is None:
        return ExhaustResult("EXHAUST_WAIT", "sin_k", in_extreme_zone=False)
    in_extreme = (direction_u == "CALL" and k <= oversold) or (
        direction_u == "PUT" and k >= overbought
    )
    if not in_extreme:
        return ExhaustResult("EXHAUST_WAIT", "fuera_de_zona_extrema", in_extreme_zone=False)

    # zona adaptativa si no la pasan
    if zone_lo is None or zone_hi is None:
        if candles_15m:
            zone_lo, zone_hi = adaptive_zone(candles_15m)
        else:
            return ExhaustResult("EXHAUST_WAIT", "sin_zona_ni_velas", in_extreme_zone=True)

    # 2) CRUCE CONFIRMADO
    ago = _cross_ago(k_vals or [], d_vals or [], direction_u)
    cross_ok = ago is not None and ago >= cross_min_ago
    if not cross_ok:
        return ExhaustResult(
            "EXHAUST_WAIT",
            "cruce_no_confirmado" + (f" (ago={ago})" if ago is not None else " (sin cruce)"),
            in_extreme_zone=True, cross_confirmed=False, cross_ago=ago,
        )

    # 2c) SEPARACION %K/%D ADAPTATIVA (R2-bis): el cruce debe salir de la
    # franja con las lineas ABIERTAS. Relativa al rango reciente de |K-D|
    # del propio par (nunca puntos fijos). Sin datos -> None (no bloquea).
    sep_ok, sep_rel = _cross_separation(k_vals or [], d_vals or [])
    if sep_ok is False:
        return ExhaustResult(
            "EXHAUST_WAIT",
            f"cruce_pegajoso:sep_rel={sep_rel}",
            in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
            separation_ok=False, separation_rel=sep_rel,
        )

    # 2b) ALINEACION M5 (R3): para que sea exitosa, M15 Y M5 deben ir en la
    # direccion de la entrada — ambas abajo para PUT, arriba para CALL.
    # Si el M5 apunta en contra -> no entra (m5_contra).
    if stoch_m5 is not None:
        m5_aligned = _m5_aligned(stoch_m5, direction_u)
        if m5_aligned is False:
            return ExhaustResult(
                "EXHAUST_WAIT",
                "m5_contra",
                in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
                m5_aligned=False,
            )
        # 2b2) M5 AGOTADO EN SU EXTREMO (R3-bis): condicion SEPARADA de R3.
        # El M5 debe estar agotado en SU propio extremo (CALL k<20 / PUT k>80)
        # en el instante de la senal. Alineado (R3) NO alcanza: el M5 puede
        # ir a favor pero ya rebotado (no agotado) -> el bot entraria en la
        # mecha, no en el fondo. R3 y R3-bis son OBLIGATORIAS por separado.
        # Razon distinta a m5_contra para que la caja negra las diferencie.
        if not _m5_exhausted(stoch_m5.get("k"), direction_u):
            return ExhaustResult(
                "EXHAUST_WAIT",
                "m5_no_exhausted",
                in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
                separation_ok=sep_ok, separation_rel=sep_rel,
                m5_aligned=True, m5_exhausted=False,
            )

    # 3a) CAMINO A — ruptura: vela de agotamiento en/cerca de la zona
    exhaustion = None
    at_franja = False
    # Banda de tolerancia de la zona (R7, endurecido): zone_strength es la
    # FUENTE PRINCIPAL de la banda cuando esta disponible. La "linea
    # imaginaria" gruesa => banda mas permisiva (la zona existe de verdad);
    # fina => banda mas estricta. Si la linea es inexistente (fuerza <
    # MIN_LINE_THICKNESS) la zona no es fiable => EXHAUST_WAIT (zona debil).
    if zone_strength is not None:
        if zone_strength < 0.20:  # MIN_LINE_THICKNESS de zone_strength.py
            return ExhaustResult(
                "EXHAUST_WAIT",
                f"zona_debil:fuerza={zone_strength:.2f}",
                in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
            )
        band = max(_zone_band(zone_lo, zone_hi) * (0.5 + zone_strength), 1e-9)
    else:
        # Fallback: adaptive_zone (rango % precio reciente) cuando no hay
        # datos de eficacia para el activo.
        band = _zone_band(zone_lo, zone_hi)
    if candles_15m:
        # INTRAVELA (R10): si se pasa candles_1m (ventana M1 de la M15 en
        # curso), la vela de rechazo se busca AHI (la M15 aun no cierra).
        # Si no, se busca en las ultimas `lookback` velas M15 cerradas.
        _src = list(candles_1m if candles_1m is not None else candles_15m)[-lookback:]
        for c in _src:
            o, h, l, cl, *_ = _candle_metrics(c)
            if direction_u == "CALL":
                # soporte: la vela llego a la zona baja (mecha o cierre)
                if (l <= zone_lo + band and cl <= zone_lo + band) or (zone_lo - band <= l <= zone_hi + band):
                    at_franja = True
                    ex = classify_exhaustion_candle(c, "CALL")
                    if ex:
                        exhaustion = ex
                        break
            else:  # PUT
                # resistencia: la vela llego a la zona alta (mecha o cierre)
                if (h >= zone_hi - band and cl >= zone_hi - band) or (zone_lo - band <= h <= zone_hi + band):
                    at_franja = True
                    ex = classify_exhaustion_candle(c, "PUT")
                    if ex:
                        exhaustion = ex
                        break

    if exhaustion is not None:
        return ExhaustResult(
            "EXHAUST_CONFIRMED",
            f"agotamiento_confirmado:ruptura:{exhaustion}",
            in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
            exhaustion_candle=exhaustion, at_support_resistance=True, path="ruptura",
            separation_ok=sep_ok, separation_rel=sep_rel,
            m5_aligned=True, m5_exhausted=True,
        )

    # 3b) CAMINO B — atrapado en extremo (tu regla USDPKR: cruces adentro de
    # 0-20/80-100 pero nunca se acerca a salir de la linea 20/80)
    trapped = _trapped_in_extreme(
        k_vals or [], d_vals or [], direction_u, oversold, overbought, trap_window
    )
    if trapped is not None:
        return ExhaustResult(
            "EXHAUST_CONFIRMED",
            f"agotamiento_confirmado:atrapado:{trapped}velas",
            in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
            at_support_resistance=False, path="atrapado",
            separation_ok=sep_ok, separation_rel=sep_rel,
            m5_aligned=True, m5_exhausted=True,
        )

    return ExhaustResult(
        "EXHAUST_WAIT",
        "sin_vela_agotamiento",
        in_extreme_zone=True, cross_confirmed=True, cross_ago=ago,
        at_support_resistance=at_franja,
        m5_aligned=True, m5_exhausted=True,
    )
