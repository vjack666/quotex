"""Connection-recovery policy for execution tasks."""
from __future__ import annotations
from typing import Any

async def ensure_connection(bot: Any, label: str = "execution") -> bool:
    ensure_fn = getattr(bot, "ensure_connection", None)
    if ensure_fn is None:
        return False
    try:
        return bool(await ensure_fn())
    except Exception:
        return False

__all__ = ["ensure_connection"]
