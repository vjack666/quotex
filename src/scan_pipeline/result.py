"""Value object for scanner output, independent from scanner orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from entry_scorer import CandidateEntry


@dataclass
class ScanResult:
    """Result of one scan cycle.

    Kept structurally identical to the legacy scanner result while giving
    downstream orchestration a stable import boundary.
    """
    candidates: list[CandidateEntry] = field(default_factory=list)
    stats_delta: dict[str, int] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)


__all__ = ["ScanResult"]
