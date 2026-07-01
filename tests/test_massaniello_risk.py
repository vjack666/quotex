"""Tests del wrapper MassanielloRiskManager."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from massaniello_risk import MassanielloRiskManager


@pytest.fixture
def mgr() -> MassanielloRiskManager:
    manager = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
    manager.set_balance(100.0)
    return manager


def test_set_balance_starts_session(mgr: MassanielloRiskManager):
    assert mgr.session_start_time is not None
    assert mgr.current_balance == 100.0
    assert mgr.entries == 0


def test_next_stake_ok(mgr: MassanielloRiskManager):
    amount, status = mgr.next_stake(92)
    assert status == "OK"
    assert amount >= 1.0
    assert amount <= 100.0


def test_three_wins_complete_session(mgr: MassanielloRiskManager):
    for _ in range(3):
        mgr.register_win(1.0, 92)
    assert mgr.is_session_complete()
    assert not mgr.can_enter()
    amount, status = mgr.next_stake(92)
    assert amount == 0.0
    assert status == "SESSION_COMPLETE"


def test_three_losses_fail_session(mgr: MassanielloRiskManager):
    for _ in range(3):
        mgr.register_loss(1.0)
    assert mgr.is_session_failed()
    assert not mgr.can_enter()
    _, status = mgr.next_stake(92)
    assert status == "SESSION_FAILED"


def test_session_timeout_blocks_entries(mgr: MassanielloRiskManager):
    old = mgr.session_start_time
    assert old is not None
    mgr.session_start_time = old - (61 * 60)
    assert mgr.is_session_timeout()
    assert not mgr.can_enter()
    _, status = mgr.next_stake(92)
    assert status == "SESSION_TIMEOUT"


def test_session_status_snapshot(mgr: MassanielloRiskManager):
    mgr.register_win(2.0, 90)
    status = mgr.session_status()
    assert status["wins"] == 1
    assert status["entries"] == 1
    assert status["operations"] == 5
    assert status["expected_wins"] == 3
    assert status["can_enter"] is True


def test_register_win_logs_session_complete(caplog, mgr: MassanielloRiskManager):
    with caplog.at_level("INFO"):
        for _ in range(3):
            mgr.register_win(1.0, 92)
    assert any("SESIÓN MASSANIELLO CUMPLIDA" in rec.message for rec in caplog.records)