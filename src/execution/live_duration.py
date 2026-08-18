"""Single access point for hot-reloaded order duration."""
from __future__ import annotations
import config as _cfg


def get() -> int:
    return int(getattr(_cfg, "DURATION_SEC", 300))

__all__ = ["get"]
