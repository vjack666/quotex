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

# pyquotex trae el cálculo base. Lo importamos para no reinventar la fórmula.
try:
    from pyquotex.utils.indicators import TechnicalIndicators
except Exception:  # pragma: no cover — fallback si pyquotex no está en path
    TechnicalIndicators = None


def _candles_to_ohlcv(candles: Sequence[Candle]) -> tuple[List[float], List[float], List[float], List[float]]:
    """Extrae close/high/low/open de una secuencia de Candle."""
    closes = [float(c.close) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    opens = [float(c.open) for c in candles]
    return closes, highs, lows, opens


def compute_stoch(
    candles: Sequence[Candle],
    k_period: int = 14,
    d_period: int = 3,
    overbought: float = 80.0,
    oversold: float = 20.0,
    direction: Optional[str] = None,
) -> Dict[str, Any]:
    """Calcula el estocástico M15 (Slow/Full 14,3) + derivados.

    Args:
        candles: velas 15m ya disponibles (htf_scanner cache).
        k_period, d_period: parámetros del estocástico.
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

    # Reutiliza la fórmula de pyquotex ( Lane clásica ).
    result = TechnicalIndicators.calculate_stochastic(closes, highs, lows, k_period, d_period)
    k_vals: List[float] = result.get("k", []) or []
    d_vals: List[float] = result.get("d", []) or []
    if not k_vals:
        return {
            "k": None, "d": None, "estado": "NEUTRO",
            "cruce": None, "divergencia": None, "contradicts": 0,
        }

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
