"""Execution session boundary.

Contains only contracts at this stage. The legacy executor remains the
behavior owner until session/risk lifecycle tests cover the extracted logic.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ExecutionSessionSnapshot:
    status: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    balance: float | None = None
    pnl: float | None = None

__all__ = ["ExecutionSessionSnapshot"]
