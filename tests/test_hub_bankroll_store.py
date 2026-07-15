"""Hub bankroll disk persistence + shape apply."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config as cfg
from hub_bankroll_store import apply_bankroll_shape_to_manager, load_bankroll, save_bankroll
from massaniello_risk import MassanielloRiskManager


def test_save_and_load_bankroll(tmp_path: Path):
    path = tmp_path / "hub_bankroll.json"
    save_bankroll(
        {
            "massaniello_ops": 7,
            "massaniello_wins": 4,
            "massaniello_virtual_capital": 40.0,
            "min_payout": 90,
            "session_max_min": 45,
        },
        path=path,
    )
    loaded = load_bankroll(path)
    assert loaded["massaniello_ops"] == 7
    assert loaded["massaniello_wins"] == 4
    assert loaded["massaniello_virtual_capital"] == 40.0
    assert loaded["min_payout"] == 90


def test_apply_shape_when_no_progress(monkeypatch):
    monkeypatch.setattr(cfg, "MASSANIELLO_OPERATIONS", 7)
    monkeypatch.setattr(cfg, "MASSANIELLO_EXPECTED_WINS", 4)
    monkeypatch.setattr(cfg, "SESSION_MAX_MIN", 60)
    mgr = MassanielloRiskManager(operations=5, expected_wins=3)
    assert mgr.operations == 5
    apply_bankroll_shape_to_manager(mgr, force=False)
    assert mgr.operations == 7
    assert mgr.expected_wins == 4


def test_apply_shape_skips_when_progress(monkeypatch):
    monkeypatch.setattr(cfg, "MASSANIELLO_OPERATIONS", 7)
    monkeypatch.setattr(cfg, "MASSANIELLO_EXPECTED_WINS", 4)
    mgr = MassanielloRiskManager(operations=5, expected_wins=3)
    mgr.wins = 2
    mgr.losses = 1
    apply_bankroll_shape_to_manager(mgr, force=False)
    assert mgr.operations == 5
    assert mgr.expected_wins == 3
