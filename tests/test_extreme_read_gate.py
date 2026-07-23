"""Tests sintéticos del extreme_read_gate (lectura de extremo, sin datos reales).

Valida la teoría empírica: el extremo es el MEJOR sitio (como un spike),
pero solo si la vela de entrada tiene CUERPO a favor de la dirección.
Si el cuerpo va contra (rebote), el gate debe RECHAZAR.

No usa ninguna DB ni red: velas Candle fake con valores conocidos.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from strat_fractal import extreme_read_gate


@dataclass
class _C:
    open: float
    high: float
    low: float
    close: float
    body: float = 0.0
    ticks: int = 0


def _win(body=0.001, rng=0.004, lo=0.690, hi=0.700):
    """Ventana de 3 velas 5m; entry en el extremo indicado por caller."""
    return [
        _C(lo + rng * 0.2, lo + rng * 0.3, lo, lo + rng * 0.25),
        _C(hi - rng * 0.3, hi - rng * 0.1, hi - rng * 0.4, hi - rng * 0.2),
        _C(lo + rng * 0.5, hi, lo, lo + rng * 0.5),  # vela ancha, todo el rango
    ]


# ── PUT que entra en MÍNIMO local con cuerpo a favor (BAJISTA) ──────────────
# Es un spike real: close < open, cuerpo dominante => debe PASAR.
def test_put_in_minimum_with_bearish_body_passes():
    candles = [
        _C(0.6990, 0.6995, 0.6988, 0.6992),
        _C(0.6988, 0.6990, 0.6982, 0.6985),
        _C(0.6985, 0.6987, 0.6980, 0.6979),  # entry 0.6980 (mínimo), cierra abajo
    ]
    ok, reason = extreme_read_gate(candles, 0.6980, "PUT")
    assert ok is True
    assert reason == "extreme_read_ok"


# ── PUT que entra en MÍNIMO local con cuerpo CONTRA (ALCISTA) = rebote ────────
# El precio ya devolvió: debe RECHAZAR.
def test_put_in_minimum_with_bullish_body_rejected():
    candles = [
        _C(0.6990, 0.6995, 0.6988, 0.6992),
        _C(0.6988, 0.6990, 0.6982, 0.6985),
        _C(0.6982, 0.6984, 0.6980, 0.6983),  # entry 0.6980 (mínimo) PERO cierra arriba
    ]
    ok, reason = extreme_read_gate(candles, 0.6980, "PUT")
    assert ok is False
    assert reason == "extreme_read_reject:body_against"


# ── CALL que entra en MÁXIMO local con cuerpo a favor (ALCISTA) => PASA ────────
def test_call_in_maximum_with_bullish_body_passes():
    candles = [
        _C(0.6980, 0.6983, 0.6979, 0.6981),
        _C(0.6983, 0.6989, 0.6982, 0.6986),
        _C(0.6986, 0.6991, 0.6985, 0.6990),  # entry 0.6991 (máximo), cierra arriba
    ]
    ok, reason = extreme_read_gate(candles, 0.6991, "CALL")
    assert ok is True
    assert reason == "extreme_read_ok"


# ── CALL que entra en MÁXIMO local con cuerpo CONTRA (BAJISTA) = rebote => RECHAZA
def test_call_in_maximum_with_bearish_body_rejected():
    candles = [
        _C(0.6980, 0.6983, 0.6979, 0.6981),
        _C(0.6983, 0.6989, 0.6982, 0.6986),
        _C(0.6989, 0.6991, 0.6988, 0.6988),  # entry 0.6991 (máximo) PERO cierra abajo
    ]
    ok, reason = extreme_read_gate(candles, 0.6991, "CALL")
    assert ok is False
    assert reason == "extreme_read_reject:body_against"


# ── Entry CENTRADA en el rango => gate abierto, no aplica lectura de extremo ──
def test_centered_entry_gate_open():
    candles = [
        _C(0.6980, 0.6983, 0.6979, 0.6981),
        _C(0.6983, 0.6989, 0.6982, 0.6986),
        _C(0.6986, 0.6991, 0.6985, 0.6985),
    ]
    ok, reason = extreme_read_gate(candles, 0.69855, "PUT")  # ~mitad del rango
    assert ok is True
    assert reason is None


# ── Sin contexto (velas vacías / entry None) => no bloquea ─────────────────────
def test_no_context_never_blocks():
    ok, reason = extreme_read_gate([], 0.6980, "PUT")
    assert ok is True
    assert reason is None
    ok2, _ = extreme_read_gate([_C(0.6980, 0.6983, 0.6979, 0.6981)], None, "CALL")
    assert ok2 is True
