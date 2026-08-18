"""Thin orchestration boundary for the scanner pipeline.

The heavy engine remains behavior-compatible while responsibilities are
extracted. New callers should depend on this boundary rather than the legacy
root module.
"""
from __future__ import annotations
from typing import Any

class ScannerOrchestrator:
    """Own one scanner engine and expose the pipeline scan-cycle entry point."""

    def __init__(self, bot: Any, executor: Any):
        from .scanner import AssetScanner
        self._engine = AssetScanner(bot, executor)

    async def scan_all(self) -> Any:
        """Run one complete scanner cycle through the behavior owner."""
        return await self._engine.scan_all()

    @property
    def engine(self) -> Any:
        """Compatibility escape hatch while internal extraction continues."""
        return self._engine

__all__ = ["ScannerOrchestrator"]
