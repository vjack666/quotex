"""Pure martingale eligibility and amount policy."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MartinDecision:
    allowed: bool
    reason: str = ""


def session_available(*, uses_massaniello: bool, used: int, limit: int) -> MartinDecision:
    if uses_massaniello:
        return MartinDecision(False, "massaniello")
    if used >= limit:
        return MartinDecision(False, "session_limit")
    return MartinDecision(True, "available")


def cap_amount(amount: float, balance: float | None) -> float:
    if balance is None:
        return max(0.0, float(amount))
    return max(0.0, min(float(amount), float(balance)))

__all__ = ["MartinDecision", "session_available", "cap_amount"]
