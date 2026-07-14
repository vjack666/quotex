"""Tests de la capa estocástica M15 (Fase 2).

Mockea TechnicalIndicators.calculate_stochastic para no depender de pyquotex
ni de red: solo validamos la capa fina (estado/cruce/divergencia/contradicts).
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import Candle
import stochastic_m15 as sm


def _candles_from_closes(closes, highs=None, lows=None):
    n = len(closes)
    highs = highs or [c * 1.01 for c in closes]
    lows = lows or [c * 0.99 for c in closes]
    return [Candle(ts=i, open=closes[i], high=highs[i], low=lows[i], close=closes[i]) for i in range(n)]


def _fake_stoch(k_seq, d_seq):
    """Simula calculate_stochastic de pyquotex: SE LLAMA UNA VEZ y devuelve
    la serie COMPLETA (recorre todas las ventanas). El código solo lee [-1]
    y [-2]."""

    def _calc(prices, highs, lows, k_period=14, d_period=3):
        return {
            "k": list(k_seq),
            "d": list(d_seq),
            "current": {"k": k_seq[-1], "d": d_seq[-1]},
        }

    return _calc


def test_overbought_state():
    closes = [100 + i for i in range(20)]  # tendencia alcista sostenida
    candles = _candles_from_closes(closes)
    # %K cerca de 100 (precio en máximo del rango)
    k_seq = [95.0] * 20
    d_seq = [90.0] * 20
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles)
    assert r["estado"] == "SOBRECOMPRA"
    assert r["k"] == 95.0


def test_oversold_state():
    closes = [200 - i for i in range(20)]  # tendencia bajista sostenida
    candles = _candles_from_closes(closes)
    k_seq = [12.0] * 20
    d_seq = [15.0] * 20
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles)
    assert r["estado"] == "SOBREVENTA"


def test_neutral_state():
    closes = [100 + (i % 3) for i in range(20)]  # rango chico
    candles = _candles_from_closes(closes)
    k_seq = [50.0] * 20
    d_seq = [50.0] * 20
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles)
    assert r["estado"] == "NEUTRO"


def test_cruce_alcista():
    closes = list(range(20))
    candles = _candles_from_closes(closes)
    # %K sube por encima de %D en el último paso
    k_seq = [40.0] * 19 + [55.0]
    d_seq = [50.0] * 19 + [52.0]
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles)
    assert r["cruce"] == "alcista"


def test_cruce_bajista():
    closes = list(range(20))
    candles = _candles_from_closes(closes)
    k_seq = [60.0] * 19 + [45.0]
    d_seq = [50.0] * 19 + [48.0]
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles)
    assert r["cruce"] == "bajista"


def test_contradicts_call_in_overbought():
    closes = [100 + i for i in range(20)]
    candles = _candles_from_closes(closes)
    k_seq = [95.0] * 20
    d_seq = [90.0] * 20
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles, direction="call")
    assert r["contradicts"] == 1


def test_contradicts_put_in_oversold():
    closes = [200 - i for i in range(20)]
    candles = _candles_from_closes(closes)
    k_seq = [12.0] * 20
    d_seq = [15.0] * 20
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles, direction="put")
    assert r["contradicts"] == 1


def test_no_divergence_short_window():
    closes = [100 + (i % 2) for i in range(20)]
    candles = _candles_from_closes(closes)
    k_seq = [50.0] * 20
    d_seq = [50.0] * 20
    with patch.object(sm, "TechnicalIndicators") as TI:
        TI.calculate_stochastic.side_effect = _fake_stoch(k_seq, d_seq)
        r = sm.compute_stoch(candles)
    assert r["divergencia"] is None


def test_insufficient_candles_returns_neutral():
    candles = _candles_from_closes([100, 101, 102])  # < 14
    with patch.object(sm, "TechnicalIndicators") as TI:
        r = sm.compute_stoch(candles)
    assert r["estado"] == "NEUTRO"
    assert r["k"] is None
