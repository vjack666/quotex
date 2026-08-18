"""State boundary for consolidation runtime.

The legacy bot remains the source of truth during migration; this protocol
prevents new state handling from leaking into orchestration code.
"""
from __future__ import annotations
from typing import Any, Protocol

class ConsolidationState(Protocol):
    def snapshot(self) -> Any: ...
    def restore(self, snapshot: Any) -> None: ...

__all__ = ["ConsolidationState"]
