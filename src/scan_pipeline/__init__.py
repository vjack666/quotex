"""Canonical scanner pipeline API.

The scanner implementation is owned by this package during the incremental
refactor. Compatibility modules at ``src/scanner.py`` and ``src/scan_prefetch.py``
remain only as import bridges for downstream callers.
"""
from .context import ScanCycleContext
from .result import ScanResult
from .scanner import AssetScanner

__all__ = ["AssetScanner", "ScanCycleContext", "ScanResult"]
