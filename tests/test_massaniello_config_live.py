"""Ops/ITM from hub config must drive real MassanielloRiskManager stakes."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config as cfg
from massaniello_engine import Settings, calculate_stake
from massaniello_risk import MassanielloRiskManager


@pytest.fixture(autouse=True)
def _restore_massaniello_config():
    old = (
        cfg.MASSANIELLO_OPERATIONS,
        cfg.MASSANIELLO_EXPECTED_WINS,
        cfg.SESSION_MAX_MIN,
        cfg.MASSANIELLO_VIRTUAL_CAPITAL,
    )
    yield
    (
        cfg.MASSANIELLO_OPERATIONS,
        cfg.MASSANIELLO_EXPECTED_WINS,
        cfg.SESSION_MAX_MIN,
        cfg.MASSANIELLO_VIRTUAL_CAPITAL,
    ) = old


def test_manager_reads_live_config_not_import_defaults():
    cfg.MASSANIELLO_OPERATIONS = 7
    cfg.MASSANIELLO_EXPECTED_WINS = 4
    mgr = MassanielloRiskManager()
    assert mgr.operations == 7
    assert mgr.expected_wins == 4


def test_manager_stake_matches_desktop_calculator_for_7_4():
    cfg.MASSANIELLO_OPERATIONS = 7
    cfg.MASSANIELLO_EXPECTED_WINS = 4
    mgr = MassanielloRiskManager()
    mgr.set_balance(30.0)
    stake, status = mgr.next_stake(92)
    assert status == "OK"
    settings = Settings(
        initial_balance=30.0,
        operations=7,
        expected_itm=4,
        profit=0.92,
        system_mode="massaniello",
    )
    expected = calculate_stake(settings, 30.0, 0, 0)
    assert expected is not None
    assert abs(stake - expected) < 0.02  # cents rounding


def test_manager_stake_changes_when_ops_itm_change():
    cfg.MASSANIELLO_OPERATIONS = 5
    cfg.MASSANIELLO_EXPECTED_WINS = 3
    a = MassanielloRiskManager()
    a.set_balance(30.0)
    stake_5_3, _ = a.next_stake(92)

    cfg.MASSANIELLO_OPERATIONS = 7
    cfg.MASSANIELLO_EXPECTED_WINS = 4
    b = MassanielloRiskManager()
    b.set_balance(30.0)
    stake_7_4, _ = b.next_stake(92)

    assert stake_5_3 != stake_7_4
    assert stake_5_3 > stake_7_4  # fewer ops → larger first stake typically
