"""Tests de strat_order_block.py."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle, OrderBlock
from strat_order_block import detect_order_block_entry


def _c(ts: int, open: float, high: float, low: float, close: float) -> Candle:
    return Candle(ts=ts, open=open, high=high, low=low, close=close)


def test_bullish_ob_returns_call():
    """OB alcista → CALL cuando el precio revisita el rango del OB."""
    candles = [
        _c(0, 1.0000, 1.0005, 0.9995, 1.0000),
        _c(60, 1.0000, 1.0010, 0.9998, 0.9998),    # OB base — roja
        _c(120, 1.0012, 1.0018, 1.0011, 1.0015),   # verde follower
        _c(180, 1.0015, 1.0022, 1.0013, 1.0020),   # verde follower
        _c(240, 1.0008, 1.0012, 0.9995, 1.0005),   # revisit — toca rango OB
        _c(300, 1.0005, 1.0010, 1.0000, 1.0007),   # filler
    ]

    ob = OrderBlock(
        side="bull",
        low=0.9998,
        high=1.0010,
        created_ts=60,
        created_index=1,
        bars_ago=0,
        is_mitigated=False,
    )

    result = detect_order_block_entry(candles, blocks=[ob])
    assert result is not None, "Bullish OB debería retornar señal"
    direction, strength, ob_low, ob_high = result
    assert direction == "call", f"Esperaba 'call', obtuve '{direction}'"
    assert 0.0 < strength <= 1.0, f"Strength {strength} fuera de rango (0, 1]"
    assert ob_low == 0.9998
    assert ob_high == 1.0010


def test_bearish_ob_returns_put():
    """OB bajista → PUT cuando el precio revisita el rango del OB."""
    candles = [
        _c(0, 1.0020, 1.0025, 1.0015, 1.0020),     # doji
        _c(60, 1.0020, 1.0030, 1.0018, 1.0028),     # OB base — verde
        _c(120, 1.0015, 1.0017, 1.0010, 1.0012),    # roja follower (fuera de rango OB)
        _c(180, 1.0012, 1.0016, 1.0008, 1.0010),    # roja follower (fuera de rango OB)
        _c(240, 1.0020, 1.0035, 1.0015, 1.0030),    # revisit — toca rango OB
        _c(300, 1.0025, 1.0028, 1.0020, 1.0025),    # filler (sin mitigación)
    ]

    ob = OrderBlock(
        side="bear",
        low=1.0018,
        high=1.0030,
        created_ts=60,
        created_index=1,
        bars_ago=0,
        is_mitigated=False,
    )

    result = detect_order_block_entry(candles, blocks=[ob])
    assert result is not None, "Bearish OB debería retornar señal"
    direction, strength, ob_low, ob_high = result
    assert direction == "put", f"Esperaba 'put', obtuve '{direction}'"
    assert 0.0 < strength <= 1.0, f"Strength {strength} fuera de rango (0, 1]"
    assert ob_low == 1.0018
    assert ob_high == 1.0030


def test_mitigated_ob_returns_none():
    """OB mitigado → None (precio cerró fuera del lado opuesto)."""
    candles = [
        _c(0, 1.0000, 1.0005, 0.9995, 1.0000),
        _c(60, 1.0000, 1.0010, 0.9998, 0.9998),     # OB base — roja
        _c(120, 1.0012, 1.0018, 1.0011, 1.0015),     # verde follower
        _c(180, 1.0015, 1.0022, 1.0013, 1.0020),     # verde follower
        _c(240, 0.9990, 0.9995, 0.9985, 0.9990),     # cierra DEBAJO de ob.low → mitigado
        _c(300, 0.9995, 1.0000, 0.9990, 0.9998),     # revisit después de mitigación
    ]

    ob = OrderBlock(
        side="bull",
        low=0.9998,
        high=1.0010,
        created_ts=60,
        created_index=1,
        bars_ago=0,
        is_mitigated=False,
    )

    result = detect_order_block_entry(candles, blocks=[ob])
    assert result is None, "OB mitigado no debería generar señal"


def test_no_ob_returns_none():
    """Sin OB → None (sin bloques)."""
    candles = [
        _c(0, 1.0000, 1.0003, 0.9997, 1.0000),
        _c(60, 1.0000, 1.0004, 0.9998, 1.0002),
        _c(120, 1.0002, 1.0005, 0.9999, 1.0003),
        _c(180, 1.0003, 1.0006, 1.0000, 1.0004),
        _c(240, 1.0004, 1.0007, 1.0001, 1.0005),
        _c(300, 1.0005, 1.0008, 1.0002, 1.0006),
    ]

    result = detect_order_block_entry(candles, blocks=[])
    assert result is None, "Sin OBs no debería generar señal"
