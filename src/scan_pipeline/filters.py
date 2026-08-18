"""Pure scanner filtering helpers.

These functions delegate no scanner orchestration and are safe to reuse from
new pipeline stages. Existing behavior remains in scanner.py until covered by
regression tests.
"""
from __future__ import annotations
from typing import Any, Callable
from data.scan_prefetch import filter_scan_assets

__all__ = ["filter_scan_assets"]
