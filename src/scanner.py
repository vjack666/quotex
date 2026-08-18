"""Compatibility facade for the canonical scanner pipeline.

New code should depend on ``scan_pipeline.ScannerOrchestrator``. The legacy
``AssetScanner`` symbol remains exported so existing callers keep working
while the engine is decomposed internally.
"""
from scan_pipeline import AssetScanner, ScanCycleContext, ScanResult, ScannerOrchestrator

__all__ = ["AssetScanner", "ScannerOrchestrator", "ScanCycleContext", "ScanResult"]
