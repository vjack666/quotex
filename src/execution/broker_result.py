"""Canonical broker settlement interpretation boundary."""
from __future__ import annotations
from typing import Any
from connection import interpret_broker_result


def interpret_settlement(win_val: Any = None, *, status: Any = None, payload: Any = None,
                         trade_amount: float = 0.0, payout_pct: int = 80):
    """Return WIN/LOSS only when broker data is settled; otherwise None."""
    return interpret_broker_result(
        win_val,
        status=status,
        payload=payload,
        trade_amount=trade_amount,
        payout_pct=payout_pct,
    )

__all__ = ["interpret_settlement"]
