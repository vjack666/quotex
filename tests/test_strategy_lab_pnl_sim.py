"""Tests verdes para src/strategy_lab/pnl_sim.py (agente C — Rentabilidad)."""
from __future__ import annotations

import numpy as np
import pytest

from strategy_lab.pnl_sim import (
    break_even_wr,
    expectancy_per_signal,
    roi_annualized,
    simulate,
)


def test_expectancy_per_signal_positive_edge():
    """El edge del freno (91% WR, 85% payout) es rentable: expectancy > 0."""
    exp = expectancy_per_signal(win_rate=0.91, payout=0.85)
    assert exp > 0.0
    # valor esperado: 0.91*0.85 - 0.09 = 0.7735 - 0.09 = 0.6835
    assert exp == pytest.approx(0.6835, abs=1e-9)


def test_break_even_wr_085():
    """Break-even WR para payout 85% ≈ 0.5405 (0.9167... / 1.7)."""
    be = break_even_wr(payout=0.85)
    assert be == pytest.approx(0.5405405405, abs=1e-6)
    # comprobación cruzada: en el break-even, expectancy debe ser ~0
    assert expectancy_per_signal(be, 0.85) == pytest.approx(0.0, abs=1e-9)


def test_simulate_known_equity():
    """Lista conocida de aciertos produce equity y ROI correctos."""
    entries = [True, False, True, True]   # 3 wins, 1 loss
    payout = 0.85
    stake = 100.0
    r = simulate(entries, payout=payout, stake=stake)
    # por señal: +85, -100, +85, +85 => neto = 155
    assert r["n"] == 4
    assert r["wins"] == 3
    assert r["total_return"] == pytest.approx(155.0, abs=1e-9)
    expected_curve = np.array([0.0, 85.0, -15.0, 70.0, 155.0])
    assert np.allclose(r["equity_curve"], expected_curve)
    # ROI = 155 / (4 * 100) = 0.3875
    assert r["roi"] == pytest.approx(0.3875, abs=1e-9)
    assert r["expectancy_realizada"] == pytest.approx(155.0 / 4, abs=1e-9)


def test_roi_annualized_simple_positive():
    """Curva simple con crecimiento positivo da ROI anualizado > 0."""
    # capital inicial 1000, tras 2 señales 1210 => +21% total
    equity = [1000.0, 1100.0, 1210.0]
    # 2 señales en 1 año -> crecimiento 1.21 anualizado = 21%
    ann = roi_annualized(equity, n_signals_per_year=2.0)
    assert ann > 0.0
    assert ann == pytest.approx(0.21, abs=1e-9)
