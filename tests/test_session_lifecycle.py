"""Smart session lifecycle: Iniciar / resume incomplete / stop on meta."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from massaniello_risk import MassanielloRiskManager
from session_manager import (
    SessionManager,
    SessionState,
    massaniello_has_progress,
    massaniello_is_terminal,
)


@pytest.fixture
def sm() -> SessionManager:
    return SessionManager()


@pytest.fixture
def mgr() -> MassanielloRiskManager:
    m = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
    m.set_balance(100.0)
    return m


class TestBootstrap:
    def test_iniciar_from_stopped_goes_scanning(self, sm: SessionManager, mgr: MassanielloRiskManager):
        mode = sm.bootstrap_for_run(mgr)
        assert mode == "fresh"
        assert sm.state == SessionState.SCANNING

    def test_resume_incomplete_session(self, sm: SessionManager, mgr: MassanielloRiskManager):
        mgr.register_win(1.0, 92)
        mgr.register_loss(1.0)
        assert massaniello_has_progress(mgr)
        assert not massaniello_is_terminal(mgr)

        mode = sm.bootstrap_for_run(mgr)
        assert mode == "resumed"
        assert sm.state == SessionState.SCANNING
        assert mgr.wins == 1
        assert mgr.losses == 1

    def test_fresh_after_completed_cycle(self, sm: SessionManager, mgr: MassanielloRiskManager):
        sm.start()
        sm.session_completed({"reason": "meta"})
        assert sm.state == SessionState.COMPLETED

        # New Massaniello for next cycle (as executor does after meta)
        clean = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
        clean.set_balance(100.0)
        mode = sm.bootstrap_for_run(clean)
        assert mode == "fresh"
        assert sm.state == SessionState.SCANNING

    def test_already_active_kept(self, sm: SessionManager, mgr: MassanielloRiskManager):
        sm.start()
        mode = sm.bootstrap_for_run(mgr)
        assert mode == "already_active"
        assert sm.state == SessionState.SCANNING

    def test_terminal_massaniello_starts_fresh_not_resume(
        self, sm: SessionManager, mgr: MassanielloRiskManager
    ):
        for _ in range(3):
            mgr.register_win(1.0, 92)
        assert massaniello_is_terminal(mgr)
        mode = sm.bootstrap_for_run(mgr)
        assert mode == "fresh"
        assert sm.state == SessionState.SCANNING


class TestTickStopOnMeta:
    def test_complete_stops_scanning(self, sm: SessionManager):
        sm.start()
        state = sm.tick(massaniello_is_complete=True)
        assert state == SessionState.COMPLETED

    def test_failed_stops_scanning(self, sm: SessionManager):
        sm.start()
        state = sm.tick(massaniello_is_failed=True)
        assert state == SessionState.COMPLETED

    def test_terminal_flag_stops_scanning(self, sm: SessionManager):
        sm.start()
        state = sm.tick(massaniello_is_terminal=True)
        assert state == SessionState.COMPLETED

    def test_force_complete_from_executor(self, sm: SessionManager):
        sm.start()
        state = sm.tick(force_complete=True)
        assert state == SessionState.COMPLETED

    def test_does_not_complete_while_open_trades_unless_forced_after_close(
        self, sm: SessionManager
    ):
        sm.start()
        sm.enter_trade()
        state = sm.tick(has_open_trades=True, massaniello_is_complete=True)
        assert state == SessionState.TRADING

        state = sm.tick(has_open_trades=False, force_complete=True)
        assert state == SessionState.COMPLETED

    def test_stopped_stays_stopped(self, sm: SessionManager):
        assert sm.tick(massaniello_is_complete=True) == SessionState.STOPPED


class TestExecutorNotifiesSessionManager:
    def test_maybe_stop_marks_session_completed(self):
        """Executor must mark COMPLETED before resetting Massaniello."""
        from executor import TradeExecutor

        bot = MagicMock()
        bot.session_stop_hit = False
        bot.massaniello = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
        bot.massaniello.set_balance(100.0)
        for _ in range(3):
            bot.massaniello.register_win(1.0, 92)
        bot.massaniello_persistence = MagicMock()

        sm = SessionManager()
        sm.start()

        client = MagicMock()
        ex = TradeExecutor(client, bot, session_manager=sm)
        # Force virtual capital path so reset runs
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("executor.MASSANIELLO_VIRTUAL_CAPITAL", 30.0)
            mp.setattr("executor.RISK_MANAGER", "massaniello")
            ex._maybe_stop_massaniello_session()

        assert bot.session_stop_hit is True
        assert sm.state == SessionState.COMPLETED
