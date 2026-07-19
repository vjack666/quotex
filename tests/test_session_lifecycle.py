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
        """Classic path: with auto-reset OFF, mark COMPLETED and stop scan."""
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
        # Force virtual capital path so reset runs; disable auto-continue
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("executor.MASSANIELLO_VIRTUAL_CAPITAL", 30.0)
            mp.setattr("executor.RISK_MANAGER", "massaniello")
            mp.setattr("executor._cfg.SESSION_AUTO_RESET_ON_COMPLETE", False)
            mp.setattr("executor._cfg.CONTINUOUS_DATA_COLLECTION_MODE", False)
            ex._maybe_stop_massaniello_session()

        assert bot.session_stop_hit is True
        assert sm.state == SessionState.COMPLETED

    def test_maybe_stop_auto_reset_keeps_scanning(self):
        """Auto-continue: reset Massaniello, no stop, no session-ended UI events."""
        from executor import TradeExecutor
        from unittest.mock import patch
        import types

        bot = MagicMock()
        bot.session_stop_hit = True  # old path would leave this True
        bot.massaniello = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
        bot.massaniello.set_balance(100.0)
        for _ in range(3):
            bot.massaniello.register_win(1.0, 92)
        bot.massaniello_persistence = MagicMock()

        sm = SessionManager()
        sm.start()
        sm.session_completed = MagicMock()  # type: ignore[method-assign]

        client = MagicMock()
        ex = TradeExecutor(client, bot, session_manager=sm)

        published: list[tuple[str, dict]] = []

        class _Bus:
            def publish(self, name: str, payload=None):
                published.append((name, payload or {}))

        fake_events = types.ModuleType("hub.events")
        fake_events.event_bus = _Bus()  # type: ignore[attr-defined]
        fake_hub = types.ModuleType("hub")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("executor.MASSANIELLO_VIRTUAL_CAPITAL", 30.0)
            mp.setattr("executor.RISK_MANAGER", "massaniello")
            mp.setattr("executor._cfg.SESSION_AUTO_RESET_ON_COMPLETE", True)
            mp.setattr("executor._cfg.CONTINUOUS_DATA_COLLECTION_MODE", True)
            with patch.dict(
                "sys.modules",
                {"hub": fake_hub, "hub.events": fake_events},
            ):
                ex._maybe_stop_massaniello_session()

        assert bot.session_stop_hit is False
        sm.session_completed.assert_not_called()
        # Fresh Massaniello after reset (0 wins)
        assert bot.massaniello.wins == 0
        assert bot.massaniello.losses == 0
        # Session stays active for scanning (not COMPLETED waiting for user)
        assert sm.state == SessionState.SCANNING
        # No session-ended notices in 24/7 auto-continue
        assert published == []
        assert not any(
            n in ("session_completed", "session_complete", "session_cycle_rolled")
            for n, _ in published
        )
