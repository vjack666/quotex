"""Tests for Massaniello bankroll preview (hub calculator card)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from massaniello_engine import Settings, calculate_stake
from massaniello_preview import build_massaniello_preview, preview_from_runner


def test_preview_matches_engine_for_5_3_30():
    prev = build_massaniello_preview(
        assigned_capital=30.0,
        operations=5,
        expected_wins=3,
        account_balance=144.54,
        payout_pct=92,
        source="config",
    )
    settings = Settings(
        initial_balance=30.0,
        operations=5,
        expected_itm=3,
        profit=0.92,
        system_mode="massaniello",
    )
    expected = calculate_stake(settings, 30.0, 0, 0)
    assert expected is not None
    assert prev["next_stake"] == round(expected, 2)
    assert prev["assigned_capital"] == 30.0
    assert prev["account_balance"] == 144.54
    assert prev["source"] == "config"
    assert prev["can_enter"] is True
    assert "OTM" in prev["status"]


def test_preview_warns_when_assigned_exceeds_balance():
    prev = build_massaniello_preview(
        assigned_capital=200.0,
        operations=5,
        expected_wins=3,
        account_balance=100.0,
    )
    assert prev["warn_assigned_gt_balance"] is True


def test_preview_after_wins_losses_uses_counters():
    prev = build_massaniello_preview(
        assigned_capital=30.0,
        operations=5,
        expected_wins=3,
        wins=2,
        losses=1,
        live_capital=24.69,
        payout_pct=92,
    )
    settings = Settings(
        initial_balance=24.69,
        operations=5,
        expected_itm=3,
        profit=0.92,
        system_mode="massaniello",
    )
    expected = calculate_stake(settings, 24.69, 2, 1)
    assert expected is not None
    assert prev["next_stake"] == round(expected, 2)
    assert prev["wins"] == 2
    assert prev["losses"] == 1


def test_preview_from_runner_config_when_stopped():
    runner = MagicMock()
    runner.get_config.return_value = {
        "massaniello_virtual_capital": 30.0,
        "massaniello_ops": 5,
        "massaniello_wins": 3,
        "_runner_state": "stopped",
    }
    runner.state = "stopped"
    runner.bot = None
    runner.get_status.return_value = {"balance": None}

    prev = preview_from_runner(runner, payout_pct=92)
    assert prev["source"] == "config"
    assert prev["assigned_capital"] == 30.0
    assert prev["next_stake"] is not None
    assert prev["next_stake"] > 0


def test_preview_from_runner_live_uses_manager():
    mgr = MagicMock()
    mgr.session_status.return_value = {
        "wins": 1,
        "losses": 0,
        "operations": 5,
        "expected_wins": 3,
        "balance": 35.0,
        "can_enter": True,
        "complete": False,
        "failed": False,
    }
    mgr.next_stake.return_value = (7.5, "OK")

    bot = SimpleNamespace(massaniello=mgr, current_balance=35.0)
    runner = MagicMock()
    runner.get_config.return_value = {
        "massaniello_virtual_capital": 30.0,
        "massaniello_ops": 5,
        "massaniello_wins": 3,
    }
    runner.state = "running"
    runner.bot = bot
    runner.get_status.return_value = {"balance": 35.0}

    prev = preview_from_runner(runner, payout_pct=92)
    assert prev["source"] == "live"
    assert prev["wins"] == 1
    assert prev["next_stake"] == 7.5
    assert prev["can_enter"] is True
