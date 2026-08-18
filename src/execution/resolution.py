"""Trade-result resolution boundary.

Only the contract is extracted in this phase. Resolution rules remain in the
legacy executor until covered by regression tests.
"""
from __future__ import annotations
from typing import Any, Protocol

class TradeResolver(Protocol):
    async def resolve(self, trade: Any) -> Any: ...

__all__ = ["TradeResolver"]
