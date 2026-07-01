"""Tests del motor Massaniello (5 ops / 3 ITM)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from massaniello_engine import Settings, calculate_stake, simulate


def _settings(balance: float = 100.0, profit: float = 1.92) -> Settings:
    return Settings(
        initial_balance=balance,
        operations=5,
        expected_itm=3,
        profit=profit,
        mode="normal",
        system_mode="massaniello",
    )


def test_calculate_stake_first_entry_positive():
    stake = calculate_stake(_settings(), capital=100.0, wins=0, losses=0)
    assert stake is not None
    assert 0.0 < stake <= 100.0


def test_simulation_three_wins_completes_session():
    sim = simulate(_settings(balance=100.0), ["w", "w", "w"])
    assert sim.wins == 3
    assert sim.losses == 0
    assert sim.finished is True
    assert sim.status == "Objetivo completado"
    assert sim.next_stake is None
    assert len(sim.rows) == 3
    assert sim.current_capital > 100.0


def test_simulation_three_losses_fails_session():
    sim = simulate(_settings(balance=100.0), ["l", "l", "l"])
    assert sim.wins == 0
    assert sim.losses == 3
    assert sim.finished is True
    assert sim.status == "Secuencia perdida"
    assert sim.next_stake is None


def test_simulation_mixed_path_reaches_target():
    sim = simulate(_settings(balance=50.0), ["w", "l", "w", "l", "w"])
    assert sim.wins == 3
    assert sim.losses == 2
    assert sim.finished is True
    assert sim.status == "Objetivo completado"


def test_simulation_exhausts_five_ops_without_target():
    sim = simulate(_settings(balance=80.0), ["w", "l", "w", "l", "l"])
    assert sim.wins == 2
    assert sim.losses == 3
    assert sim.finished is True
    assert sim.status == "Secuencia perdida"


def test_settings_validation_rejects_invalid_itm():
    with pytest.raises(ValueError):
        Settings(operations=5, expected_itm=6).validate()