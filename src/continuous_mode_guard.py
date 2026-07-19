"""Continuous Mode Guard — Strategy-based safety guardrails.

Applies the Strategy pattern so each safety rule can evolve independently
without modifying the others. All strategies live in this single file
to avoid file proliferation.

Strategies:
- ConsecutiveLossStrategy: pause after N consecutive losses
- DailyLossStrategy: stop after X% daily capital loss
- RateLimitStrategy: enforce minimum interval between entries

The ContinuousModeGuard is now a thin coordinator that holds a list of
strategies and delegates to them. Adding a new rule means creating a new
strategy class and registering it — no changes to existing code.

Usage:
    guard = ContinuousModeGuard(initial_capital=30.0)
    # Strategies are created automatically with config defaults.
    # To customize:
    guard = ContinuousModeGuard(
        initial_capital=30.0,
        strategies=[
            ConsecutiveLossStrategy(max_losses=5, pause_minutes=10),
            DailyLossStrategy(daily_limit=0.20),
        ],
    )
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

log = logging.getLogger(__name__)


# ── Strategy interface ─────────────────────────────────────────────────


class GuardStrategy(ABC):
    """Base interface for all continuous mode safety strategies.

    Each strategy implements only the methods it needs. The guard coordinator
    calls all methods and aggregates results.

    Lifecycle:
    - on_loss() / on_win() — called on every trade result
    - should_block() — checked before each scan cycle
    - reset_daily() — called at midnight or new day
    - status() — for logging/API
    """

    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name for logging."""
        ...

    def on_loss(self, amount: float) -> None:
        """Called when a trade loss is registered. Default: no-op."""

    def on_win(self) -> None:
        """Called when a trade win is registered. Default: no-op."""

    def should_block(self) -> bool:
        """Return True if this strategy wants to block scanning. Default: False."""
        return False

    def block_reason(self) -> str:
        """Why this strategy is blocking. Empty if not blocking."""
        return ""

    def reset_daily(self) -> None:
        """Reset daily counters. Default: no-op."""

    def status(self) -> dict:
        """Strategy-specific status for logging/API. Default: empty."""
        return {}


# ── Concrete strategies ────────────────────────────────────────────────


class ConsecutiveLossStrategy(GuardStrategy):
    """Pause scanning after N consecutive losses.

    Rationale: a streak of losses may indicate unfavorable market conditions.
    A brief pause lets the market regime change before resuming.
    """

    def __init__(self, max_losses: int = 8, pause_minutes: int = 15) -> None:
        self._max_losses = max_losses
        self._pause_minutes = pause_minutes
        self._consecutive = 0
        self._pause_until: Optional[float] = None
        self._pause_reason: str = ""

    def name(self) -> str:
        return "consecutive_loss"

    def on_loss(self, amount: float) -> None:
        self._consecutive += 1
        if self._consecutive >= self._max_losses:
            self._trigger_pause(
                f"{self._consecutive} consecutive losses (limit={self._max_losses})"
            )

    def on_win(self) -> None:
        self._consecutive = 0

    def should_block(self) -> bool:
        if self._pause_until is None:
            return False
        if time.time() >= self._pause_until:
            self._pause_until = None
            self._pause_reason = ""
            log.info("Continuous mode: consecutive loss pause ended — resuming")
            return False
        return True

    def block_reason(self) -> str:
        return self._pause_reason

    def status(self) -> dict:
        return {
            "consecutive_losses": self._consecutive,
            "is_paused": self.should_block(),
            "pause_remaining_min": round(self._pause_remaining_min(), 1),
        }

    # ── Internal ─────────────────────────────────────────────────────

    def _trigger_pause(self, reason: str) -> None:
        self._pause_reason = reason
        self._pause_until = time.time() + (self._pause_minutes * 60.0)
        log.warning(
            "⚠️ Continuous mode PAUSED: %s — reanuda en %d min",
            reason,
            self._pause_minutes,
        )

    def _pause_remaining_min(self) -> float:
        if self._pause_until is None:
            return 0.0
        return max(0.0, (self._pause_until - time.time()) / 60.0)

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive

    def pause_remaining_min(self) -> float:
        return self._pause_remaining_min()


class DailyLossStrategy(GuardStrategy):
    """Stop continuous mode after X% of initial capital is lost in one day.

    Rationale: prevents runaway losses during extended 24/7 runs.
    The bot must be restarted manually after a daily stop.
    """

    def __init__(self, initial_capital: float, daily_limit: float = 0.30) -> None:
        self._initial_capital = float(initial_capital)
        self._daily_limit = daily_limit
        self._total_losses_today = 0.0
        self._day_start = time.time()

    def name(self) -> str:
        return "daily_loss"

    def on_loss(self, amount: float) -> None:
        self._total_losses_today += float(amount)

    def should_block(self) -> bool:
        return self.is_limit_hit()

    def block_reason(self) -> str:
        if self.is_limit_hit():
            return (
                f"Daily loss limit reached: "
                f"{self.loss_ratio() * 100:.1f}% >= {self._daily_limit * 100:.0f}%"
            )
        return ""

    def reset_daily(self) -> None:
        self._total_losses_today = 0.0
        self._day_start = time.time()
        log.info("Continuous mode: daily loss counters reset")

    def status(self) -> dict:
        return {
            "daily_loss_ratio": round(self.loss_ratio(), 4),
            "daily_limit_hit": self.is_limit_hit(),
        }

    def is_limit_hit(self) -> bool:
        if self._initial_capital <= 0:
            return False
        return self.loss_ratio() >= self._daily_limit

    def loss_ratio(self) -> float:
        if self._initial_capital <= 0:
            return 0.0
        return self._total_losses_today / self._initial_capital


class RateLimitStrategy(GuardStrategy):
    """Enforce minimum time between trade entries.

    Rationale: prevents the bot from entering trades too frequently,
    which could overwhelm the broker or indicate a scanning issue.
    """

    def __init__(self, min_interval_sec: float = 30.0) -> None:
        self._min_interval = min_interval_sec
        self._last_entry_time: Optional[float] = None

    def name(self) -> str:
        return "rate_limit"

    def can_enter(self) -> bool:
        if self._last_entry_time is None:
            return True
        return (time.time() - self._last_entry_time) >= self._min_interval

    def seconds_until_entry(self) -> float:
        if self._last_entry_time is None:
            return 0.0
        return max(0.0, self._min_interval - (time.time() - self._last_entry_time))

    def record_entry(self) -> None:
        self._last_entry_time = time.time()

    def status(self) -> dict:
        return {
            "can_enter_now": self.can_enter(),
            "seconds_until_next_entry": round(self.seconds_until_entry(), 1),
        }


# ── Guard coordinator ──────────────────────────────────────────────────


class ContinuousModeGuard:
    """Coordinator for continuous mode safety strategies.

    Holds a list of GuardStrategy instances and delegates trade results
    and blocking checks to them. This is the single point of interaction
    for the orchestrator.

    Default strategies are created automatically. Custom strategies can
    be passed via the ``strategies`` parameter.
    """

    def __init__(
        self,
        initial_capital: float,
        max_consecutive_losses: int = 8,
        pause_minutes: int = 15,
        daily_loss_limit: float = 0.30,
        min_trade_interval_sec: float = 30.0,
        strategies: Optional[list[GuardStrategy]] = None,
    ) -> None:
        if strategies is not None:
            self._strategies = list(strategies)
        else:
            self._strategies = [
                ConsecutiveLossStrategy(
                    max_losses=max_consecutive_losses,
                    pause_minutes=pause_minutes,
                ),
                DailyLossStrategy(
                    initial_capital=initial_capital,
                    daily_limit=daily_loss_limit,
                ),
                RateLimitStrategy(min_interval_sec=min_trade_interval_sec),
            ]

    # ── Trade result delegation ──────────────────────────────────────

    def register_loss(self, amount: float = 0.0) -> None:
        """Notify all strategies of a loss."""
        for strategy in self._strategies:
            strategy.on_loss(amount)

    def register_win(self) -> None:
        """Notify all strategies of a win."""
        for strategy in self._strategies:
            strategy.on_win()

    # ── Blocking checks (aggregates all strategies) ──────────────────

    def should_pause(self) -> bool:
        """Return True if any strategy wants to block scanning."""
        return any(s.should_block() for s in self._strategies)

    def pause_reason(self) -> str:
        """Return the reason from the first blocking strategy."""
        for s in self._strategies:
            reason = s.block_reason()
            if reason:
                return reason
        return ""

    def pause_remaining_min(self) -> float:
        """Minutes remaining in current pause (0 if not paused)."""
        for s in self._strategies:
            if hasattr(s, "pause_remaining_min"):
                remaining = s.pause_remaining_min()
                if remaining > 0:
                    return remaining
        return 0.0

    def is_daily_limit_hit(self) -> bool:
        """Check if the daily loss strategy limit has been exceeded."""
        for s in self._strategies:
            if isinstance(s, DailyLossStrategy):
                return s.is_limit_hit()
        return False

    def daily_loss_ratio(self) -> float:
        """Current daily loss as fraction of initial capital."""
        for s in self._strategies:
            if isinstance(s, DailyLossStrategy):
                return s.loss_ratio()
        return 0.0

    def reset_daily(self) -> None:
        """Reset daily counters on all strategies that support it."""
        for s in self._strategies:
            s.reset_daily()

    # ── Rate limiting delegation ─────────────────────────────────────

    def can_enter_now(self) -> bool:
        """Check if rate limiting allows an entry now."""
        for s in self._strategies:
            if isinstance(s, RateLimitStrategy):
                return s.can_enter()
        return True

    def seconds_until_next_entry(self) -> float:
        """Seconds to wait before next allowed entry."""
        for s in self._strategies:
            if isinstance(s, RateLimitStrategy):
                return s.seconds_until_entry()
        return 0.0

    def record_entry(self) -> None:
        """Mark that an entry was made."""
        for s in self._strategies:
            if isinstance(s, RateLimitStrategy):
                s.record_entry()

    # ── Status ───────────────────────────────────────────────────────

    @property
    def consecutive_losses(self) -> int:
        """Expose consecutive losses for testing/logging."""
        for s in self._strategies:
            if isinstance(s, ConsecutiveLossStrategy):
                return s.consecutive_losses
        return 0

    def status(self) -> dict:
        """Aggregate status from all strategies."""
        result: dict = {}
        for s in self._strategies:
            result[s.name()] = s.status()
        return result
