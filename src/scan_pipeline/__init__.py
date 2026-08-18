"""Canonical scanner pipeline API.

Implementation imports stay lazy to avoid cycles with connection/executor.
New callers should use ``ScannerOrchestrator``; ``AssetScanner`` remains a
compatibility escape hatch while the engine is decomposed internally.
"""
from .context import ScanCycleContext
from .result import ScanResult
from .orchestrator import ScannerOrchestrator

__all__ = ["ScannerOrchestrator", "AssetScanner", "ScanCycleContext", "ScanResult"]


def __getattr__(name: str):
    if name == "AssetScanner":
        from .scanner import AssetScanner
        return AssetScanner
    raise AttributeError(name)
