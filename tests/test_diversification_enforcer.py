"""Tests de diversification_enforcer.py."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from unittest.mock import MagicMock

import pytest

from diversification_enforcer import DiversificationEnforcer
from models import TradeState


def _make_trade(asset: str) -> TradeState:
    return TradeState(
        asset=asset,
        direction="call",
        amount=1.0,
        entry_price=1.0,
        ceiling=1.1,
        floor=0.9,
    )


# ── R1: Límite global de trades simultáneos ─────────────────────────────────


def test_allows_below_max_simultaneous():
    """Entrada permitida cuando hay espacio."""
    enforcer = DiversificationEnforcer(max_simultaneous_trades=3, min_asset_spread=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "GBPUSD_otc")
    assert ok is True, f"Esperaba permitir, obtuve: {reason}"


def test_rejects_exceeding_max_simultaneous():
    """Entrada rechazada cuando se alcanzó el límite global."""
    enforcer = DiversificationEnforcer(max_simultaneous_trades=2)
    trades = {
        "EURUSD_otc": _make_trade("EURUSD_otc"),
        "GBPUSD_otc": _make_trade("GBPUSD_otc"),
    }
    ok, reason = enforcer.check(trades, "USDJPY_otc")
    assert ok is False
    assert "max_simultaneous_trades" in reason


def test_rejects_when_exactly_at_limit():
    """Rechaza cuando el número de abiertos es exactamente el límite."""
    enforcer = DiversificationEnforcer(max_simultaneous_trades=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "GBPUSD_otc")
    assert ok is False
    assert "max_simultaneous_trades" in reason


# ── R2: Spread mínimo de activos ────────────────────────────────────────────


def test_rejects_low_asset_spread():
    """Rechaza cuando todos los trades abiertos son sobre un mismo activo."""
    enforcer = DiversificationEnforcer(min_asset_spread=2)
    # Todos en EURUSD_otc — solo 1 activo distinto
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "EURUSD_otc")
    assert ok is False
    assert "min_asset_spread" in reason


def test_allows_high_asset_spread():
    """Permite cuando hay suficientes activos distintos."""
    enforcer = DiversificationEnforcer(min_asset_spread=2)
    trades = {
        "EURUSD_otc": _make_trade("EURUSD_otc"),
        "GBPUSD_otc": _make_trade("GBPUSD_otc"),
    }
    ok, reason = enforcer.check(trades, "USDJPY_otc")
    assert ok is True, f"Esperaba permitir, obtuve: {reason}"


# ── R3: Máximo de entradas concurrentes por activo ──────────────────────────


def test_rejects_exceeding_max_per_asset():
    """Rechaza cuando el activo ya tiene el máximo de entradas."""
    enforcer = DiversificationEnforcer(max_entries_per_asset=1, min_asset_spread=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "EURUSD_otc")
    assert ok is False
    assert "max_entries_per_asset" in reason


def test_rejects_exceeding_max_per_asset_with_spread():
    """Cuando ambos límites aplican, min_asset_spread rechaza primero."""
    enforcer = DiversificationEnforcer(
        max_entries_per_asset=2, min_asset_spread=2,
    )
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "EURUSD_otc")
    assert ok is False
    # Con 1 único activo, spread se dispara antes que entries_per_asset
    assert "min_asset_spread" in reason


def test_allows_different_asset_when_one_asset_full():
    """Permite entrada en otro activo aunque el máximo por activo se alcanzó."""
    enforcer = DiversificationEnforcer(max_entries_per_asset=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "GBPUSD_otc")
    assert ok is True, f"Esperaba permitir, obtuve: {reason}"


# ── R4: Logging (verificamos estructura del mensaje de rechazo) ────────────


def test_rejection_reason_contains_asset_and_limit(caplog):
    """El mensaje de rechazo incluye activo y límite violado."""
    import logging
    caplog.set_level(logging.INFO)
    enforcer = DiversificationEnforcer(max_simultaneous_trades=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, _ = enforcer.check(trades, "GBPUSD_otc")
    assert ok is False
    assert any("EURUSD_otc" not in r.message and "GBPUSD_otc" in r.message and "max_simultaneous_trades" in r.message
               for r in caplog.records), "Log debería mencionar el activo candidato y el límite"


# ── R5: Cero trades abiertos ────────────────────────────────────────────────


def test_allows_when_zero_trades():
    """Siempre permite cuando no hay trades abiertos."""
    enforcer = DiversificationEnforcer(
        max_simultaneous_trades=1, min_asset_spread=2, max_entries_per_asset=1,
    )
    ok, reason = enforcer.check({}, "EURUSD_otc")
    assert ok is True, f"Esperaba permitir sin trades, obtuve: {reason}"


# ── Exención de martingala ─────────────────────────────────────────────────


def test_allows_martin_exempt():
    """Martingala no es bloqueada por diversificación."""
    enforcer = DiversificationEnforcer(max_simultaneous_trades=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "GBPUSD_otc", stage="martin")
    assert ok is True, f"Martin debería estar exento: {reason}"


def test_allows_breakout_exempt():
    """Breakout no es bloqueado por diversificación."""
    enforcer = DiversificationEnforcer(max_simultaneous_trades=1)
    trades = {"EURUSD_otc": _make_trade("EURUSD_otc")}
    ok, reason = enforcer.check(trades, "GBPUSD_otc", stage="breakout")
    assert ok is True, f"Breakout debería estar exento: {reason}"


# ── Sin límites (0 = desactivado) ──────────────────────────────────────────


def test_zero_max_simultaneous_means_no_limit():
    """max_simultaneous_trades=0 desactiva el límite global."""
    enforcer = DiversificationEnforcer(max_simultaneous_trades=0)
    trades = {
        "A": _make_trade("A"),
        "B": _make_trade("B"),
        "C": _make_trade("C"),
    }
    ok, reason = enforcer.check(trades, "D")
    assert ok is True, f"0 debería desactivar el límite: {reason}"
