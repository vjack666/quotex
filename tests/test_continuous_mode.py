"""Tests for Continuous Data Collection Mode.

Tests cover:
- ContinuousModeGuard safety guardrails (consecutive losses, daily limit, rate limiting)
- ContinuousModeOrchestrator delegation and session reset behavior
- Configuration loading
- Normal operation is not affected when continuous mode is off
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure src/ is on the path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ── ContinuousModeGuard tests ─────────────────────────────────────────────


class TestContinuousModeGuard:
    """Tests for the ContinuousModeGuard safety layer (pure, no config deps)."""

    def _make_guard(self, **kwargs):
        from continuous_mode_guard import ContinuousModeGuard
        defaults = {"initial_capital": 30.0}
        defaults.update(kwargs)
        return ContinuousModeGuard(**defaults)

    def test_initial_state(self):
        guard = self._make_guard()
        assert guard.consecutive_losses == 0
        assert not guard.should_pause()
        assert not guard.is_daily_limit_hit()
        assert guard.can_enter_now()

    def test_register_win_resets_consecutive(self):
        guard = self._make_guard(max_consecutive_losses=3)
        guard.register_loss(1.0)
        guard.register_loss(1.0)
        assert guard.consecutive_losses == 2
        guard.register_win()
        assert guard.consecutive_losses == 0

    def test_consecutive_loss_pause(self):
        guard = self._make_guard(max_consecutive_losses=3, pause_minutes=10)
        guard.register_loss(1.0)
        guard.register_loss(1.0)
        assert not guard.should_pause()
        guard.register_loss(1.0)
        assert guard.should_pause()
        assert guard.pause_remaining_min() > 0
        assert "3 consecutive losses" in guard.pause_reason()

    def test_pause_expires(self, monkeypatch):
        guard = self._make_guard(max_consecutive_losses=2, pause_minutes=5)
        guard.register_loss(1.0)
        guard.register_loss(1.0)
        assert guard.should_pause()

        # Fake time forward past the pause
        fake_now = time.time() + (6 * 60)  # 6 minutes later
        monkeypatch.setattr(time, "time", lambda: fake_now)
        assert not guard.should_pause()

    def test_daily_loss_limit(self):
        guard = self._make_guard(initial_capital=100.0, daily_loss_limit=0.30)
        # 29% loss — not hit yet
        guard.register_loss(29.0)
        assert not guard.is_daily_limit_hit()
        assert guard.daily_loss_ratio() == pytest.approx(0.29)
        # 30% loss — hit
        guard.register_loss(1.0)
        assert guard.is_daily_limit_hit()
        assert guard.daily_loss_ratio() == pytest.approx(0.30)

    def test_daily_reset(self):
        guard = self._make_guard(initial_capital=100.0, daily_loss_limit=0.30)
        guard.register_loss(50.0)
        assert guard.is_daily_limit_hit()
        guard.reset_daily()
        assert not guard.is_daily_limit_hit()
        assert guard.daily_loss_ratio() == 0.0

    def test_rate_limiting(self, monkeypatch):
        guard = self._make_guard(min_trade_interval_sec=30)
        assert guard.can_enter_now()
        assert guard.seconds_until_next_entry() == 0.0

        guard.record_entry()
        assert not guard.can_enter_now()
        assert guard.seconds_until_next_entry() == pytest.approx(30.0, abs=1.0)

        # Fake time forward
        fake_now = time.time() + 31
        monkeypatch.setattr(time, "time", lambda: fake_now)
        assert guard.can_enter_now()
        assert guard.seconds_until_next_entry() == 0.0

    def test_status_dict(self):
        guard = self._make_guard()
        status = guard.status()
        # Status is now nested by strategy name
        assert "consecutive_loss" in status
        assert "daily_loss" in status
        assert "rate_limit" in status
        assert "consecutive_losses" in status["consecutive_loss"]
        assert "daily_loss_ratio" in status["daily_loss"]
        assert "daily_limit_hit" in status["daily_loss"]
        assert "is_paused" in status["consecutive_loss"]
        assert "can_enter_now" in status["rate_limit"]

    def test_zero_capital_guard(self):
        guard = self._make_guard(initial_capital=0.0)
        # With zero capital, daily limit should never trigger (avoid div by zero)
        guard.register_loss(100.0)
        assert not guard.is_daily_limit_hit()

    def test_pause_does_not_block_win_registration(self):
        """Even when paused, registering a win should reset consecutive counter."""
        guard = self._make_guard(max_consecutive_losses=2, pause_minutes=10)
        guard.register_loss(1.0)
        guard.register_loss(1.0)
        assert guard.should_pause()
        guard.register_win()
        assert guard.consecutive_losses == 0
        # Still paused though (pause is time-based)
        assert guard.should_pause()


# ── ContinuousModeOrchestrator tests ─────────────────────────────────────


class TestContinuousModeOrchestrator:
    """Tests for the orchestrator that connects guard to bot lifecycle."""

    def _make_orchestrator(self, **guard_kwargs):
        from continuous_mode import ContinuousModeOrchestrator
        from continuous_mode_guard import ContinuousModeGuard
        defaults = {"initial_capital": 30.0}
        defaults.update(guard_kwargs)
        guard = ContinuousModeGuard(**defaults)
        return ContinuousModeOrchestrator(guard=guard, log_startup=False)

    def _make_mock_bot(self, virtual_capital=30.0):
        bot = MagicMock()
        bot.executor._massaniello_virtual.return_value = virtual_capital
        bot.current_balance = 25.0
        return bot

    def test_should_skip_scan_when_paused(self):
        orch = self._make_orchestrator(max_consecutive_losses=2, pause_minutes=10)
        orch.guard.register_loss(1.0)
        orch.guard.register_loss(1.0)
        assert orch.should_skip_scan() is True

    def test_should_skip_scan_when_daily_limit_hit(self):
        orch = self._make_orchestrator(initial_capital=100.0, daily_loss_limit=0.30)
        orch.guard.register_loss(30.0)
        assert orch.should_skip_scan() is True

    def test_should_not_skip_scan_when_ok(self):
        orch = self._make_orchestrator()
        assert orch.should_skip_scan() is False

    def test_should_stop_entirely(self):
        orch = self._make_orchestrator(initial_capital=100.0, daily_loss_limit=0.30)
        assert orch.should_stop_entirely() is False
        orch.guard.register_loss(30.0)
        assert orch.should_stop_entirely() is True

    def test_reset_session_resets_massaniello(self):
        orch = self._make_orchestrator()
        bot = self._make_mock_bot()

        # Simulate a completed Massaniello
        bot.massaniello = MagicMock()
        bot.massaniello.wins = 3
        bot.massaniello.losses = 0
        bot.session_stop_hit = True

        orch.reset_session(bot)

        # Verify Massaniello was replaced
        assert bot.session_stop_hit is False
        bot.session_manager.bootstrap_for_run.assert_called_once()
        bot.executor.set_session_start_balance.assert_called_once()

    def test_register_win_delegates_to_guard(self):
        orch = self._make_orchestrator(max_consecutive_losses=3)
        orch.guard.register_loss(1.0)
        orch.guard.register_loss(1.0)
        orch.register_win()
        assert orch.guard.consecutive_losses == 0

    def test_register_loss_delegates_to_guard(self):
        orch = self._make_orchestrator(max_consecutive_losses=3)
        orch.register_loss(amount=2.0)
        assert orch.guard.consecutive_losses == 1

    def test_rate_limiting_delegation(self, monkeypatch):
        orch = self._make_orchestrator(min_trade_interval_sec=30)
        assert orch.can_enter_now() is True
        orch.record_entry()
        assert orch.can_enter_now() is False
        fake_now = time.time() + 31
        monkeypatch.setattr(time, "time", lambda: fake_now)
        assert orch.can_enter_now() is True

    def test_status_includes_mode(self):
        orch = self._make_orchestrator()
        status = orch.status()
        assert status["mode"] == "continuous"
        assert "guard" in status


# ── Config tests ──────────────────────────────────────────────────────────


class TestContinuousConfig:
    """Tests for continuous mode configuration."""

    def test_default_enabled(self):
        import config
        # Product default: continuous collection + Massaniello auto-reset (24/7)
        assert config.CONTINUOUS_DATA_COLLECTION_MODE is True
        assert config.SESSION_AUTO_RESET_ON_COMPLETE is True

    def test_safety_defaults_exist(self):
        import config
        assert config.CONTINUOUS_MAX_CONSECUTIVE_LOSSES > 0
        assert config.CONTINUOUS_PAUSE_AFTER_LOSSES_MIN > 0
        assert 0 < config.CONTINUOUS_DAILY_LOSS_LIMIT <= 1.0
        assert config.CONTINUOUS_MIN_TRADE_INTERVAL_SEC > 0


# ── Normal mode isolation tests ───────────────────────────────────────────


class TestNormalModeIsolation:
    """Prove that normal mode behavior is unchanged when continuous is off."""

    def test_massaniello_not_affected_by_continuous_guard(self):
        """MassanielloRiskManager should work normally without continuous guard."""
        from massaniello_risk import MassanielloRiskManager

        mgr = MassanielloRiskManager(operations=5, expected_wins=3, session_max_min=60)
        mgr.set_balance(30.0)

        # Normal session limits still apply
        assert mgr.can_enter()
        mgr.register_win(1.0, 92)
        mgr.register_win(1.0, 92)
        mgr.register_win(1.0, 92)
        assert mgr.is_session_complete()
        assert not mgr.can_enter()

    def test_session_manager_not_affected(self):
        """SessionManager should work normally without continuous mode."""
        from session_manager import SessionManager, SessionState

        sm = SessionManager()
        assert sm.state == SessionState.STOPPED
        sm.start()
        assert sm.state == SessionState.SCANNING
        sm.stop()
        assert sm.state == SessionState.STOPPED


# ── Strategy pattern extensibility tests ──────────────────────────────────


class TestStrategyPattern:
    """Validate that the Strategy pattern allows adding new rules easily."""

    def test_custom_strategy_can_be_added(self):
        """Prove a new strategy can be injected without modifying existing code."""
        from continuous_mode_guard import (
            ContinuousModeGuard,
            GuardStrategy,
            ConsecutiveLossStrategy,
            DailyLossStrategy,
        )

        class MaxTradesStrategy(GuardStrategy):
            """Example custom strategy: stop after N total trades."""

            def __init__(self, max_trades: int = 50) -> None:
                self._max = max_trades
                self._count = 0

            def name(self) -> str:
                return "max_trades"

            def on_loss(self, amount: float) -> None:
                self._count += 1

            def on_win(self) -> None:
                self._count += 1

            def should_block(self) -> bool:
                return self._count >= self._max

            def block_reason(self) -> str:
                if self.should_block():
                    return f"Max trades reached: {self._count}/{self._max}"
                return ""

        # Create guard with custom strategy list
        guard = ContinuousModeGuard(
            initial_capital=30.0,
            strategies=[
                ConsecutiveLossStrategy(max_losses=8, pause_minutes=15),
                DailyLossStrategy(initial_capital=30.0, daily_limit=0.30),
                MaxTradesStrategy(max_trades=3),
            ],
        )

        # First two trades: no block
        guard.register_loss(1.0)
        guard.register_win()
        assert not guard.should_pause()

        # Third trade: max reached → block
        guard.register_loss(1.0)
        assert guard.should_pause()
        assert "Max trades reached" in guard.pause_reason()

    def test_strategies_are_independent(self):
        """Prove strategies don't interfere with each other's state."""
        from continuous_mode_guard import (
            ContinuousModeGuard,
            ConsecutiveLossStrategy,
            DailyLossStrategy,
            RateLimitStrategy,
        )

        guard = ContinuousModeGuard(
            initial_capital=100.0,
            strategies=[
                ConsecutiveLossStrategy(max_losses=2, pause_minutes=1),
                DailyLossStrategy(initial_capital=100.0, daily_limit=0.50),
                RateLimitStrategy(min_interval_sec=0),  # no rate limit
            ],
        )

        # Two losses trigger consecutive pause but NOT daily limit
        guard.register_loss(10.0)
        guard.register_loss(10.0)
        assert guard.should_pause()  # consecutive loss pause
        assert not guard.is_daily_limit_hit()  # only 20% lost, limit is 50%

    def test_strategy_interface_has_sensible_defaults(self):
        """Prove the abstract base provides no-op defaults."""
        from continuous_mode_guard import GuardStrategy

        class MinimalStrategy(GuardStrategy):
            def name(self) -> str:
                return "minimal"

        strategy = MinimalStrategy()
        # All default methods should work without raising
        assert strategy.should_block() is False
        assert strategy.block_reason() == ""
        strategy.on_loss(1.0)  # no-op
        strategy.on_win()  # no-op
        strategy.reset_daily()  # no-op
        assert strategy.status() == {}
