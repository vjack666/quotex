"""Pure amount/profit calculations used by order execution.

No broker or bot state is accessed here. Keeping arithmetic pure makes it
safe to test independently before moving the stateful stake selection out of
``executor.py``.
"""
from __future__ import annotations
from math import ceil


def round_up_to_cents(value: float) -> float:
    return ceil(max(0.0, float(value)) * 100.0) / 100.0


def expected_profit(amount: float, payout_pct: int | float) -> float:
    payout_rate = max(0.01, float(payout_pct) / 100.0)
    return round_up_to_cents(float(amount) * payout_rate)


def cap_to_balance(amount: float, balance: float | None, max_pct: float, minimum: float) -> float:
    if balance is None or balance <= 0:
        return max(float(minimum), round_up_to_cents(amount))
    capped = round_up_to_cents(float(balance) * float(max_pct))
    return max(float(minimum), capped if amount > capped else round_up_to_cents(amount))

__all__ = ["round_up_to_cents", "expected_profit", "cap_to_balance"]
