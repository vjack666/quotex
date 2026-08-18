"""Thin orchestration boundary for the scanner pipeline.

The heavy engine remains behavior-compatible while responsibilities are
extracted. New callers should depend on this boundary rather than the legacy
root module.
"""
from __future__ import annotations
from typing import Any

class ScannerOrchestrator:
    """Own one scanner engine and expose only the pipeline entry point."""

    def __init__(self, bot: Any, executor: Any):
        # Lazy import prevents the pipeline package from creating import cycles
        # with executor/connection during application startup.
        from .scanner import AssetScanner
        self._engine = AssetScanner(bot, executor)

    async def scan(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate one scan cycle to the behavior-preserving engine."""
        return await self._engine.scan(*args, **kwargs)

    @property
    def engine(self) -> Any:
        """Expose the engine only for compatibility during migration."""
        return self._engine

__all__ = ["ScannerOrchestrator"]
