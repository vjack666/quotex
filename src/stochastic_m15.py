"""Estocástico M15 para STRAT-F — capa fina sobre pyquotex.

REUTILIZA la implementación de pyquotex (TechnicalIndicators.calculate_stochastic,
pyquotex/utils/indicators.py:114) que ya trae la fórmula clásica de Lane
(%K = (close - min_low)/(max_high - min_low)*100; %D = SMA 3 de %K). NO
reinventamos la fórmula: menos bug, idéntica a la documentación del libro
(boblioteca/estocastico/).

Esta capa añade lo que pyquotex NO calcula:
- estado: SOBRECOMPRA (>=80) / SOBREVENTA (<=20) / NEUTRO
- cruce: %K vs %D (alcista / bajista / None)
- divergencia: bull / bear / None (precio vs %K en ventana reciente)
- contradicts: si el estocástico va contra la dirección STRAT-F

Modo MEDICIÓN (arranque): calcula y devuelve, no filtra. El A/B de la caja
negra decide si se promueve a veto.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from models import Candle

# pyquotex trae el cálculo base del %K crudo. Lo importamos para no reinventar
# la fórmula de Lane.
try:
    from pyquotex.utils.indicators import TechnicalIndicators
except Exception:  # pragma: no cover — fallback si pyquotex no está en path
    TechnicalIndicators = None


def _sma(values: List[float], period: int) -> List[float]:
    """SMA simple local (usada para suavizar %K y calcular %D). Evita depender
    de pyquotex en el suavizado y simplifica los tests."""
    if period <= 0 or len(values) < period:
        return []
    out = []
    for i in range(len(values) - period + 1):
        out.append(round(sum(values[i:i + period]) / period, 2))
    return out


def _candles_to_ohlcv(candles: Sequence[Candle]) -> tuple[List[float], List[float], List[float], List[float]]:
    """Extrae close/high/low/open de una secuencia de Candle."""
    closes = [float(c.close) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    opens = [float(c.open) for c in candles]
    return closes, highs, lows, opens


def _cross_ago_in_series(
    k_vals: List[float], d_vals: List[float], cruce: Optional[str]
) -> Optional[int]:
    """Velas M15 desde el ULTIMO cruce %K/%D en la direccion de `cruce`.

    cruce='alcista' busca K subiendo sobre D; 'bajista' busca K bajando
    bajo D. Devuelve n velas hace, o None si no hay cruce en la serie.
    """
    if cruce is None or len(k_vals) < 2 or len(d_vals) < 2:
        return None
    cross_idx: Optional[int] = None
    n = min(len(k_vals), len(d_vals))  # %D suele ser mas corta que %K
    for i in range(1, n):
        k0, d0, k1, d1 = k_vals[i - 1], d_vals[i - 1], k_vals[i], d_vals[i]
        if cruce == "alcista" and k0 <= d0 and k1 > d1:
            cross_idx = i
        elif cruce == "bajista" and k0 >= d0 and k1 < d1:
            cross_idx = i
    if cross_idx is None:
        return None
    return len(k_vals) - 1 - cross_idx


def _cruce_en_zona(
    k_vals: Sequence[float],
    d_vals: Sequence[float],
    cruce: Optional[str],
    overbought: float,
    oversold: float,
) -> bool:
    """True si el ULTIMO cruce %K/%D ocurrió MIENTRAS el %K estaba en la banda
    de extremo (>=overbought o <=oversold). Esto es la condición de estrategia
    'cruce en zona de sobrecompra/sobreventa', no un cruce en neutro.

    Un cruce en el medio del termómetro (20-80) NO cuenta: la estrategia solo
    opera el agotamiento en el extremo.
    """
    if cruce is None or len(k_vals) < 2 or len(d_vals) < 2:
        return False
    n = min(len(k_vals), len(d_vals))
    cross_idx: Optional[int] = None
    for i in range(1, n):
        k0, d0, k1, d1 = k_vals[i - 1], d_vals[i - 1], k_vals[i], d_vals[i]
        if cruce == "alcista" and k0 <= d0 and k1 > d1:
            cross_idx = i
        elif cruce == "bajista" and k0 >= d0 and k1 < d1:
            cross_idx = i
    if cross_idx is None:
        return False
    k_at_cross = k_vals[cross_idx]
    return k_at_cross >= overbought or k_at_cross <= oversold


def compute_stoch(
    candles: Sequence[Candle],
    k_period: int = 14,
    d_period: int = 3,
    slow_k_period: int = 3,
    overbought: float = 80.0,
    oversold: float = 20.0,
    direction: Optional[str] = None,
) -> Dict[str, Any]:
    """Calcula el estocástico FULL 14,3,3 (igual a la plataforma Quotex: 14 3 SMA:3 80 20).

    Parámetros coinciden con el indicador de la plataforma:
      - %K periodo 14 (Lane clásico, sin suavizar).
      - %K suavizado por SMA de `slow_k_period` (3) -> es la línea %K que muestra
        la plataforma ("SMA:3").
      - %D periodo `d_period` (3) = SMA de %K suavizado.

    Args:
        candles: velas ya disponibles (htf_scanner cache).
        k_period, d_period: parámetros del estocástico.
        slow_k_period: suavizado SMA del %K (3 = igual a plataforma). Poner 1
            para usar el %K crudo (Slow 14,3, sin suavizar).
        overbought, oversold: umbrales de extremo.
        direction: "call"/"put" opcional para calcular `contradicts`.

    Returns:
        {
          "k": float|None, "d": float|None,
          "estado": "SOBRECOMPRA"|"SOBREVENTA"|"NEUTRO",
          "cruce": "alcista"|"bajista"|None,
          "divergencia": "bull"|"bear"|None,
          "contradicts": 0|1,
        }
    """
    closes, highs, lows, _opens = _candles_to_ohlcv(candles)

    # Sin suficientes velas: devolver neutro, no romper el scan.
    if TechnicalIndicators is None or len(closes) < k_period:
        return {
            "k": None, "d": None, "estado": "NEUTRO",
            "cruce": None, "divergencia": None, "contradicts": 0,
        }

    # Reutiliza la fórmula de pyquotex (Lane clásica) -> %K crudo(14), %D=SMA3(%K crudo).
    result = TechnicalIndicators.calculate_stochastic(closes, highs, lows, k_period, d_period)
    k_crudo: List[float] = result.get("k", []) or []
    if not k_crudo:
        return {
            "k": None, "d": None, "estado": "NEUTRO",
            "cruce": None, "divergencia": None, "contradicts": 0,
        }

    # Full Stochastic 14,3,3: suaviza el %K crudo con SMA(slow_k_period) para
    # obtener la línea %K que muestra la plataforma; %D = SMA3 de esa línea.
    if slow_k_period and slow_k_period > 1:
        k_smooth: List[float] = _sma(k_crudo, slow_k_period)
    else:
        k_smooth = k_crudo
    if len(k_smooth) < d_period:
        # sin suficientes velas suavizadas para el %D
        return {
            "k": None, "d": None, "estado": "NEUTRO",
            "cruce": None, "divergencia": None, "contradicts": 0,
        }
    d_vals: List[float] = _sma(k_smooth, d_period)
    k_vals = k_smooth  # el análisis (cruce/estado/divergencia) usa el %K suavizado

    k = round(float(k_vals[-1]), 2)
    d = round(float(d_vals[-1]), 2) if d_vals else None

    # Estado de extremo
    if k >= overbought:
        estado = "SOBRECOMPRA"
    elif k <= oversold:
        estado = "SOBREVENTA"
    else:
        estado = "NEUTRO"

    # Cruce %K vs %D (necesitamos al menos 2 valores para ver dirección)
    cruce = None
    if d is not None and len(k_vals) >= 2 and len(d_vals) >= 2:
        if k > d and k_vals[-2] <= d_vals[-2]:
            cruce = "alcista"
        elif k < d and k_vals[-2] >= d_vals[-2]:
            cruce = "bajista"

    # Antiguedad del cruce en velas M15 (>=1 = confirmado ~5 min).
    cross_ago = _cross_ago_in_series(k_vals, d_vals, cruce)

    # El cruce ocurrio DENTRO de la banda de extremo? (condicion de estrategia:
    # cruce %K/%D en sobrecompra/sobreventa, no en neutro).
    cruce_en_zona = _cruce_en_zona(k_vals, d_vals, cruce, overbought, oversold)

    # Divergencia (precio vs %K en ventana reciente, mín 3 velas)
    divergencia = _detect_divergence(closes, k_vals)

    # Contradicción con la dirección STRAT-F:
    # CALL quiere sobreventa (rebote) => SOBRECOMPRA sostenida lo contradice.
    # PUT quiere sobrecompra (rebote) => SOBREVENTA sostenida lo contradice.
    # Normalize direction to lowercase for comparison (evaluate_strat_f returns
    # "CALL"/"PUT" but this function expects "call"/"put").
    _dir = (direction or "").lower()
    contradicts = 0
    if _dir == "call" and estado == "SOBRECOMPRA":
        contradicts = 1
    elif _dir == "put" and estado == "SOBREVENTA":
        contradicts = 1

    return {
        "k": k, "d": d, "estado": estado,
        "cruce": cruce, "divergencia": divergencia, "contradicts": contradicts,
        "k_prev": k_vals[-2] if len(k_vals) >= 2 else None,
        "cross_ago": cross_ago,  # velas M15 desde el cruce (>=1 = confirmado ~5 min)
        "cruce_en_zona": cruce_en_zona,  # el cruce ocurrio en banda 80/20 (no en neutro)
        "k_vals": k_vals, "d_vals": d_vals,  # series para agotamiento confirmado
    }


def _detect_divergence(closes: List[float], k_vals: List[float], window: int = 5) -> Optional[str]:
    """Detecta divergencia precio vs %K en la ventana reciente.

    bull: precio hace mínimo más bajo pero %K mínimo más alto.
    bear: precio hace máximo más alto pero %K máximo más bajo.
    """
    if len(closes) < window or len(k_vals) < window:
        return None
    pc, pk = closes[-window:], k_vals[-window:]
    price_lower_low = pc[-1] < min(pc[:-1])
    price_higher_high = pc[-1] > max(pc[:-1])
    k_higher_low = pk[-1] > min(pk[:-1])
    k_lower_high = pk[-1] < max(pk[:-1])
    if price_lower_low and k_higher_low:
        return "bull"
    if price_higher_high and k_lower_high:
        return "bear"
    return None
