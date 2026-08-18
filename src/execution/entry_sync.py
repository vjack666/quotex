"""Small, dependency-free entry synchronization helpers."""
from __future__ import annotations
from typing import Any


def normalize_direction(direction: Any) -> str:
    value = str(direction or "").strip().lower()
    if value in {"call", "buy", "up"}:
        return "call"
    if value in {"put", "sell", "down"}:
        return "put"
    return value


def is_direction(direction: Any, expected: str) -> bool:
    return normalize_direction(direction) == normalize_direction(expected)

__all__ = ["normalize_direction", "is_direction"]
