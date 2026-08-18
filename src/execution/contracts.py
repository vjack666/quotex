"""Stable contracts for execution extraction.

These protocols describe boundaries only; they do not change the current
broker implementation or order/risk behavior.
"""
from __future__ import annotations

from typing import Any, Protocol


class BrokerExecutor(Protocol):
    async def place_order(self, asset: str, direction: str, amount: float, duration: int, **kwargs: Any) -> Any:
        """Submit an order through the broker adapter."""


class TradeResolver(Protocol):
    async def resolve(self, trade_id: Any, **kwargs: Any) -> Any:
        """Resolve a previously submitted trade."""
