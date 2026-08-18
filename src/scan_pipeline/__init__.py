"""Canonical scanner pipeline API.

The package intentionally keeps scanner implementation imports lazy to avoid
cycles between the compatibility facade and pipeline submodules.
"""
from .context import ScanCycleContext
from .result import ScanResult

__all__ = ["AssetScanner", "ScanCycleContext", "ScanResult"]


def __getattr__(name: str):
    if name == "AssetScanner":
        from .scanner import AssetScanner
        return AssetScanner
    raise AttributeError(name)
