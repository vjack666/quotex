"""Session lifecycle manager for the Quotex trading bot.

Manages the state machine: STOPPED → SCANNING → TRADING → COMPLETED → RESETTING → SCANNING
"""
from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Optional

from config import SESSION_COOLDOWN_MINUTES

log = logging.getLogger(__name__)

# Lazy import to avoid circular deps
_event_bus = None


def _get_event_bus():
    global _event_bus
    if _event_bus is None:
        try:
            from hub.events import event_bus
            _event_bus = event_bus
        except ImportError:
            pass
    return _event_bus


class SessionState(str, Enum):
    STOPPED = "stopped"
    SCANNING = "scanning"
    TRADING = "trading"
    COMPLETED = "completed"
    RESETTING = "resetting"


class SessionManager:
    """Manages session lifecycle with explicit states.

    States:
        STOPPED    - Bot is not running
        SCANNING   - Actively looking for trade entries
        TRADING    - Has open positions, waiting for results
        COMPLETED  - Session reached 3 ITM or 3 OTM, waiting for user confirmation
        RESETTING  - Preparing for new cycle (clearing Massaniello state)
    """

    def __init__(self, cooldown_minutes: int = SESSION_COOLDOWN_MINUTES) -> None:
        self._state = SessionState.STOPPED
        self._cooldown_minutes = cooldown_minutes
        self._cooldown_until: Optional[float] = None
        self._cycle_count = 0
        self._last_trade_reason: Optional[str] = None
        self._last_trade_info: Optional[dict] = None
        self._session_start_time: Optional[float] = None

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def last_trade_reason(self) -> Optional[str]:
        return self._last_trade_reason

    @property
    def last_trade_info(self) -> Optional[dict]:
        return self._last_trade_info

    @property
    def session_start_time(self) -> Optional[float]:
        return self._session_start_time

    def start(self) -> None:
        """Transition from STOPPED to SCANNING."""
        if self._state != SessionState.STOPPED:
            log.debug("SessionManager.start() called from state %s, ignoring", self._state)
            return
        self._state = SessionState.SCANNING
        self._session_start_time = time.time()
        self._emit_state_changed()
        log.info("🔍 Session started — SCANNING")

    def stop(self) -> None:
        """Transition to STOPPED from any state."""
        old = self._state
        self._state = SessionState.STOPPED
        self._session_start_time = None
        self._emit_state_changed()
        log.info("⏹ Session stopped (was %s)", old.value)

    def enter_trade(self) -> None:
        """Transition from SCANNING to TRADING."""
        if self._state != SessionState.SCANNING:
            log.debug("enter_trade() called from state %s, ignoring", self._state)
            return
        self._state = SessionState.TRADING
        self._emit_state_changed()

    def exit_trade(self) -> None:
        """Transition from TRADING back to SCANNING."""
        if self._state != SessionState.TRADING:
            log.debug("exit_trade() called from state %s, ignoring", self._state)
            return
        self._state = SessionState.SCANNING
        self._emit_state_changed()

    def session_completed(self, summary: Optional[dict] = None) -> None:
        """Mark session as completed (3 ITM or 3 OTM reached).

        Emits session_completed event for the dashboard modal.
        """
        if self._state in (SessionState.COMPLETED, SessionState.STOPPED):
            return
        self._state = SessionState.COMPLETED
        self._cycle_count += 1
        self._emit_state_changed()

        bus = _get_event_bus()
        if bus is not None:
            bus.publish("session_completed", summary or {})
        log.info(
            "✅ Session completed (cycle #%d) — waiting for user confirmation",
            self._cycle_count,
        )

    def confirm_new_cycle(self) -> None:
        """User confirmed they want a new cycle.

        Transitions: COMPLETED → RESETTING → SCANNING
        """
        if self._state != SessionState.COMPLETED:
            log.debug("confirm_new_cycle() called from state %s, ignoring", self._state)
            return

        self._state = SessionState.RESETTING
        self._emit_state_changed()
        log.info("🔄 Starting new cycle (cycle #%d)...", self._cycle_count + 1)

        # Immediate reset (no cooldown)
        self._state = SessionState.SCANNING
        self._session_start_time = time.time()
        self._emit_state_changed()

        bus = _get_event_bus()
        if bus is not None:
            bus.publish("session_reset", {"cycle": self._cycle_count + 1})
        log.info("🔍 New cycle started — SCANNING")

    def reject_new_cycle(self) -> None:
        """User declined new cycle. Transition to STOPPED."""
        if self._state != SessionState.COMPLETED:
            return
        self._state = SessionState.STOPPED
        self._session_start_time = None
        self._emit_state_changed()
        log.info("⏹ User declined new cycle — STOPPED")

    def set_trade_reason(self, reason: str, trade_info: Optional[dict] = None) -> None:
        """Store the reason for the last trade (for display in dashboard)."""
        self._last_trade_reason = reason
        self._last_trade_info = trade_info

    def tick(self, massaniello_is_complete: bool = False, massaniello_is_failed: bool = False, has_open_trades: bool = False) -> SessionState:
        """Called each scan cycle to update state.

        Args:
            massaniello_is_complete: True if Massaniello reached 3 ITM
            massaniello_is_failed: True if Massaniello reached 3 OTM
            has_open_trades: True if there are open positions

        Returns:
            Current session state
        """
        if self._state == SessionState.STOPPED:
            return self._state

        if self._state == SessionState.RESETTING:
            return self._state

        if self._state == SessionState.COMPLETED:
            # Stay in COMPLETED until user confirms
            return self._state

        if self._state == SessionState.TRADING:
            if not has_open_trades:
                self.exit_trade()
            return self._state

        # SCANNING state
        if has_open_trades:
            self.enter_trade()
            return self._state

        if massaniello_is_complete or massaniello_is_failed:
            self.session_completed()
            return self._state

        return self._state

    def get_status(self) -> dict[str, Any]:
        """Return current session status for API/dashboard."""
        elapsed = 0.0
        if self._session_start_time is not None:
            elapsed = (time.time() - self._session_start_time) / 60.0

        return {
            "state": self._state.value,
            "cycle_count": self._cycle_count,
            "session_start_time": self._session_start_time,
            "elapsed_minutes": round(elapsed, 1),
            "last_trade_reason": self._last_trade_reason,
            "last_trade_info": self._last_trade_info,
        }

    def _emit_state_changed(self) -> None:
        """Emit state_changed event."""
        bus = _get_event_bus()
        if bus is not None:
            bus.publish("state_changed", {"state": self._state.value, "cycle": self._cycle_count})
