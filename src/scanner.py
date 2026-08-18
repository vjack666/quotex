"""Compatibility facade for the canonical scanner pipeline.

The implementation lives in ``scan_pipeline.scanner`` while shared scanner
contracts are exposed from dedicated pipeline modules.
"""
from scan_pipeline.scanner import *  # noqa: F401,F403
from scan_pipeline.result import ScanResult

__all__ = [name for name in globals() if not name.startswith("_")]
