"""Pure settlement classification for execution results."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Settlement:
    outcome: str
    win: bool = False
    loss: bool = False
    open: bool = False
    reason: str = ""


def classify(result: Any) -> Settlement:
    if result is None:
        return Settlement("OPEN", open=True, reason="no_result")
    if isinstance(result, dict):
        status = str(result.get("status", result.get("outcome", ""))).lower()
        if status in {"win", "won", "profit", "itm"} or result.get("win") is True:
            return Settlement("WIN", win=True)
        if status in {"loss", "lost", "otm"} or result.get("loss") is True:
            return Settlement("LOSS", loss=True)
        if status in {"open", "pending", "unsettled"}:
            return Settlement("OPEN", open=True, reason=status)
    return Settlement("OPEN", open=True, reason="unclassified")

__all__ = ["Settlement", "classify"]
