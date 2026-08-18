"""Execution lifecycle boundary extracted from the monolithic executor.

This module defines stable contracts first. Existing ``TradeExecutor`` keeps
ownership of behavior until each lifecycle concern can be moved and tested
independently; no order/risk policy is duplicated here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class TradeLifecycle(Protocol):
    """Minimal lifecycle contract for an execution coordinator."""

    async def execute(self, candidate: Any) -> Any: ...
    async def resolve(self, trade: Any) -> Any: ...


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable context passed between execution stages."""
    symbol: str
    direction: str
    amount: float
    duration_sec: int


__all__ = ["TradeLifecycle", "ExecutionContext"]
