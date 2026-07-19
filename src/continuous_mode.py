"""Continuous Data Collection Mode — Orchestrator.

Centralizes all continuous mode behavior so that consolidation_bot.py and
executor.py delegate to a single module instead of scattering logic.

Responsibilities:
- Create and manage the ContinuousModeGuard instance.
- Decide whether to bypass Massaniello session limits.
- Handle session reset when a cycle completes (keep scanning).
- Check daily reset, pause state, and daily loss limit.
- Provide clear logging at mode boundaries.

Non-responsibilities:
- Does NOT modify MassanielloRiskManager or session logic for normal mode.
- Does NOT implement safety guardrails (delegates to continuous_mode_guard.py).
- Does NOT interact with schedule_auto (feature #8) — they are independent.

Interaction with schedule_auto:
    Continuous mode and schedule_auto are mutually exclusive operational modes.
    If schedule_auto is active (feature #8), it controls when the bot runs.
    Continuous mode (--continuous) runs the bot 24/7 with safety guardrails.
    They should NOT be activated simultaneously. If both flags are somehow
    set, continuous mode takes precedence (data collection priority).

Architecture alignment:
    This module sits at the "execution + risk management" layer.
    It wraps Massaniello session behavior without modifying it,
    following the decorator pattern for session lifecycle control.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional, Protocol

import config as _cfg
from continuous_mode_guard import ContinuousModeGuard

log = logging.getLogger(__name__)


# ── Protocol for the bot interface (avoids circular imports) ─────────────


class _BotLike(Protocol):
    """Minimal interface the orchestrator needs from ConsolidationBot."""

    executor: Any
    massaniello: Any
    session_manager: Any
    session_stop_hit: bool
    current_balance: Optional[float]
    _continuous_last_day: str


class _MassanielloLike(Protocol):
    """Minimal interface for MassanielloRiskManager."""

    wins: int
    losses: int
    operations: int
    expected_wins: int

    def is_session_complete(self) -> bool: ...
    def is_session_failed(self) -> bool: ...
    def is_session_timeout(self) -> bool: ...
    def is_session_exhausted(self) -> bool: ...


# ── Orchestrator ─────────────────────────────────────────────────────────


class ContinuousModeOrchestrator:
    """Orchestrates continuous data collection mode.

    This is the single entry point for all continuous mode behavior.
    consolidation_bot.py should call methods on this class instead of
    implementing continuous mode logic inline.

    Usage:
        orchestrator = ContinuousModeOrchestrator.from_bot(bot)
        # In main loop, before scanning:
        if orchestrator.should_skip_scan():
            await asyncio.sleep(60)
            continue
        # After session completes:
        if orchestrator.should_reset_session():
            orchestrator.reset_session(bot)
    """

    def __init__(
        self,
        guard: ContinuousModeGuard,
        log_startup: bool = True,
    ) -> None:
        self.guard = guard
        self._log_startup = log_startup

    @classmethod
    def from_bot(cls, bot: _BotLike) -> "ContinuousModeOrchestrator":
        """Create orchestrator from a ConsolidationBot instance.

        Reads virtual capital from the bot's executor to size the guard.
        """
        vcap = bot.executor._massaniello_virtual()
        guard_capital = vcap if vcap is not None else (bot.current_balance or 30.0)
        guard = ContinuousModeGuard(initial_capital=guard_capital)

        if cls._should_log_startup():
            log.info(
                "🔄 CONTINUOUS MODE activo — recolección de datos 24/7 (PRACTICE only) | "
                "capital=%.2f | max_consecutive_losses=%d | daily_loss_limit=%.0f%%",
                guard_capital,
                _cfg.CONTINUOUS_MAX_CONSECUTIVE_LOSSES,
                _cfg.CONTINUOUS_DAILY_LOSS_LIMIT * 100,
            )

        return cls(guard=guard, log_startup=False)

    @staticmethod
    def _should_log_startup() -> bool:
        """Avoid duplicate startup logs when called from bot init."""
        return True

    # ── Pre-scan checks ──────────────────────────────────────────────

    def should_skip_scan(self) -> bool:
        """Return True if the scan cycle should be skipped this iteration.

        Reasons to skip:
        - Guard is in forced pause (consecutive losses).
        - Daily loss limit has been reached.
        """
        # Modo 24h: sin frenos de guard (pausa ni límite diario).
        # Flag INDEPENDIENTE de STAKE_MODE (gestión Massaniello).
        if not getattr(_cfg, "DAILY_LOSS_GUARD_ENABLED", True):
            return False

        if self.guard.should_pause():
            remaining = self.guard.pause_remaining_min()
            log.info(
                "⏸ CONTINUOUS MODE: paused (%s) — %.1f min restantes, skip scan",
                self.guard.pause_reason(),
                remaining,
            )
            return True

        if self.guard.is_daily_limit_hit():
            log.warning(
                "⛔ CONTINUOUS MODE: daily loss limit reached (%.1f%%) — stopping",
                self.guard.daily_loss_ratio() * 100,
            )
            return True

        return False

    def should_stop_entirely(self) -> bool:
        """Return True if the bot should stop running completely."""
        if not getattr(_cfg, "DAILY_LOSS_GUARD_ENABLED", True):
            return False
        return self.guard.is_daily_limit_hit()

    # ── Daily reset ──────────────────────────────────────────────────

    def check_daily_reset(self, bot: _BotLike) -> None:
        """Check if a new day started and reset daily counters.

        Call this once per scan cycle, before scanning.
        """
        today = time.strftime("%Y-%m-%d", time.gmtime())
        last_day = getattr(bot, "_continuous_last_day", None)
        if last_day != today:
            self.guard.reset_daily()
            bot._continuous_last_day = today  # type: ignore[attr-defined]

    # ── Session completion handling ──────────────────────────────────

    def should_reset_session(self, bot: _BotLike) -> bool:
        """Return True if Massaniello should be reset and scanning continued.

        In continuous mode, when a Massaniello session completes (wins/losses/
        timeout), we reset it and keep scanning instead of stopping.
        """
        return True  # Always reset in continuous mode (caller checks guardrails first)

    def reset_session(self, bot: _BotLike) -> None:
        """Reset Massaniello for a fresh cycle and re-bootstrap the session.

        This is the key difference from normal mode:
        - Normal mode: session completes → scan stops → user must press "Iniciar"
        - Continuous mode: session completes → reset Massaniello → keep scanning
        """
        from massaniello_risk import MassanielloRiskManager

        bot.massaniello = MassanielloRiskManager()
        vcap = bot.executor._massaniello_virtual()
        if vcap is not None:
            bot.executor.set_session_start_balance(vcap)
        bot.session_manager.bootstrap_for_run(bot.massaniello, force_new=True)
        bot.session_stop_hit = False

        log.info(
            "🔄 CONTINUOUS MODE: Massaniello reset — nuevo ciclo de datos "
            "(sesión previa: %dW/%dL)",
            bot.massaniello.wins,
            bot.massaniello.losses,
        )

    # ── Trade result registration (delegates to guard) ───────────────

    def register_win(self) -> None:
        """Notify guard of a win (resets consecutive loss counter)."""
        self.guard.register_win()

    def register_loss(self, amount: float) -> None:
        """Notify guard of a loss (increments consecutive counter, checks limits)."""
        self.guard.register_loss(amount=amount)

    # ── Rate limiting (delegates to guard) ───────────────────────────

    def can_enter_now(self) -> bool:
        """Check if enough time has passed since last entry."""
        return self.guard.can_enter_now()

    def seconds_until_next_entry(self) -> float:
        """Seconds to wait before next allowed entry."""
        return self.guard.seconds_until_next_entry()

    def record_entry(self) -> None:
        """Mark that an entry was made (for rate limiting)."""
        self.guard.record_entry()

    # ── Status ───────────────────────────────────────────────────────

    def status(self) -> dict:
        """Current orchestrator + guard status for logging/API."""
        return {
            "mode": "continuous",
            "guard": self.guard.status(),
        }
