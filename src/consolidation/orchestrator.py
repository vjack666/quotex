"""Consolidation orchestration boundary.

``ConsolidationBot`` remains the compatibility entry point and behavior
owner. This module defines the narrow coordination contract so state/policy/
execution concerns can be extracted incrementally without changing runtime
rules.
"""
from __future__ import annotations

from typing import Any, Protocol


class ConsolidationOrchestrator(Protocol):
    """Coordinate one consolidation cycle without owning its policies."""

    async def run_cycle(self) -> Any: ...


__all__ = ["ConsolidationOrchestrator"]
