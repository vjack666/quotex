"""Gestión de sesión Massaniello para el bot Quotex."""
from __future__ import annotations

import logging
import time
from math import ceil
from typing import Any, Optional, Tuple

from alerter import alerter
import config as _cfg
from config import MIN_ORDER_AMOUNT
from massaniello_engine import Settings, calculate_stake, effective_profit

# Lazy import to avoid circular deps at module level
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

log = logging.getLogger(__name__)


class MassanielloRiskManager:
    """Wrapper de sesión Massaniello (ops / ITM / límite temporal).

    Ops/ITM se leen de ``config`` en el momento de crear la instancia (no al
    importar el módulo), para que el hub (capital + Ops/ITM) actualice el motor
    real de stakes — misma fórmula que la calculadora Desktop/massaniello.
    """

    def __init__(
        self,
        operations: Optional[int] = None,
        expected_wins: Optional[int] = None,
        session_max_min: Optional[int] = None,
    ) -> None:
        # Read LIVE module values (hub may have changed them via /api/config).
        ops = int(operations if operations is not None else _cfg.MASSANIELLO_OPERATIONS)
        ew = int(expected_wins if expected_wins is not None else _cfg.MASSANIELLO_EXPECTED_WINS)
        smm = int(session_max_min if session_max_min is not None else _cfg.SESSION_MAX_MIN)
        if ops < 1:
            ops = 1
        if ew < 1:
            ew = 1
        if ew > ops:
            ew = ops
        self.operations = ops
        self.expected_wins = ew
        self.session_max_min = smm
        self.session_start_time: Optional[float] = None
        self.entries = 0
        self.wins = 0
        self.losses = 0
        self.current_balance: Optional[float] = None
        self._initial_capital: Optional[float] = None
        log.info(
            "MassanielloRiskManager listo: %d ops / %d ITM / max %d min (motor calculadora)",
            self.operations,
            self.expected_wins,
            self.session_max_min,
        )

    @staticmethod
    def _round_up_cents(amount: float) -> float:
        return ceil(max(0.0, amount) * 100.0) / 100.0

    def _played(self) -> int:
        return self.wins + self.losses

    def set_balance(self, capital: float) -> None:
        capital = max(0.0, float(capital))
        self.current_balance = capital
        if self.session_start_time is None:
            self.session_start_time = time.time()
            self._initial_capital = capital

    def _settings(self, payout_pct: int) -> Settings:
        profit = effective_profit(float(payout_pct) / 100.0)
        base = self._initial_capital if self._initial_capital is not None else (self.current_balance or 0.0)
        return Settings(
            initial_balance=max(base, 0.01),
            operations=self.operations,
            expected_itm=self.expected_wins,
            profit=profit,
            mode="normal",
            system_mode="massaniello",
        )

    def is_session_complete(self) -> bool:
        return self.wins >= self.expected_wins

    def is_session_failed(self) -> bool:
        max_losses = self.operations - self.expected_wins + 1
        return self.losses >= max_losses

    def is_session_timeout(self) -> bool:
        if self.session_start_time is None:
            return False
        elapsed_min = (time.time() - self.session_start_time) / 60.0
        return elapsed_min >= float(self.session_max_min)

    def is_session_exhausted(self) -> bool:
        return self._played() >= self.operations

    def can_enter(self) -> bool:
        if self.current_balance is None or self.current_balance < MIN_ORDER_AMOUNT:
            return False
        if self.is_session_complete():
            return False
        if self.is_session_failed():
            return False
        if self.is_session_timeout():
            return False
        if self.is_session_exhausted():
            return False
        return True

    def next_stake(self, payout_pct: int) -> Tuple[float, str]:
        if not self.can_enter():
            if self.is_session_complete():
                return 0.0, "SESSION_COMPLETE"
            if self.is_session_failed():
                return 0.0, "SESSION_FAILED"
            if self.is_session_timeout():
                return 0.0, "SESSION_TIMEOUT"
            if self.is_session_exhausted():
                return 0.0, "SESSION_EXHAUSTED"
            return 0.0, "NO_BALANCE"

        settings = self._settings(payout_pct)
        raw = calculate_stake(settings, float(self.current_balance), self.wins, self.losses)
        if raw is None:
            return 0.0, "SESSION_FINISHED"

        stake = self._round_up_cents(raw)
        stake = max(MIN_ORDER_AMOUNT, stake)
        if stake > float(self.current_balance):
            stake = self._round_up_cents(float(self.current_balance))
        if stake < MIN_ORDER_AMOUNT:
            return 0.0, "INSUFFICIENT_BALANCE"
        return stake, "OK"

    def register_win(self, amount: float, payout_pct: int) -> Tuple[float, str]:
        if self.current_balance is None:
            return 0.0, "NO_BALANCE"

        payout_rate = max(0.01, float(payout_pct) / 100.0)
        profit = float(amount) * payout_rate
        old = self.current_balance
        self.current_balance = old + profit
        self.wins += 1
        self.entries += 1

        status = "WIN"
        if self.is_session_complete():
            status = "SESSION_COMPLETE"
            log.info(
                "🎯 SESIÓN MASSANIELLO CUMPLIDA — %d/%d ITM en sesión",
                self.wins,
                self.expected_wins,
            )
            alerter.alert_session_complete(self.wins, self.current_balance or 0.0)
            bus = _get_event_bus()
            if bus is not None:
                bus.publish("session_complete", {
                    "wins": self.wins,
                    "expected_wins": self.expected_wins,
                    "balance": self.current_balance,
                    "session_max_min": self.session_max_min,
                    "elapsed_min": (time.time() - self.session_start_time) / 60.0 if self.session_start_time else 0,
                })
        return self.current_balance, status

    def register_loss(self, amount: float) -> Tuple[float, str]:
        if self.current_balance is None:
            return 0.0, "NO_BALANCE"

        old = self.current_balance
        self.current_balance = max(0.0, old - float(amount))
        self.losses += 1
        self.entries += 1

        status = "LOSS"
        if self.is_session_failed():
            status = "SESSION_FAILED"
            alerter.alert_losing_streak(self.losses, self.current_balance or 0.0)
        elif self.is_session_exhausted():
            status = "SESSION_EXHAUSTED"
        return self.current_balance, status

    def session_status(self) -> dict[str, Any]:
        elapsed_min = 0.0
        if self.session_start_time is not None:
            elapsed_min = (time.time() - self.session_start_time) / 60.0
        return {
            "session_start_time": self.session_start_time,
            "entries": self.entries,
            "wins": self.wins,
            "losses": self.losses,
            "operations": self.operations,
            "expected_wins": self.expected_wins,
            "balance": self.current_balance,
            "initial_capital": self._initial_capital,
            "can_enter": self.can_enter(),
            "complete": self.is_session_complete(),
            "failed": self.is_session_failed(),
            "timeout": self.is_session_timeout(),
            "exhausted": self.is_session_exhausted(),
            "elapsed_min": elapsed_min,
            "session_max_min": self.session_max_min,
        }