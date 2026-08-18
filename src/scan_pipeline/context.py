"""Shared context for one scanner cycle.

This is deliberately dependency-light. It carries fetched market data and
runtime references without importing the legacy scanner implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass
class ScanCycleContext:
    symbols: list[str] = field(default_factory=list)
    candles: dict[str, Any] = field(default_factory=dict)
    secondary: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    runtime: Any = None

__all__ = ["ScanCycleContext"]
