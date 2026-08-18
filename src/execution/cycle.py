"""Pure cycle accounting helpers for the execution lifecycle."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CycleSnapshot:
    operations: int
    wins: int
    losses: int
    profit: float


def apply_outcome(snapshot: CycleSnapshot, outcome: str, profit: float) -> CycleSnapshot:
    if outcome not in {"WIN", "LOSS"}:
        return snapshot
    return CycleSnapshot(
        operations=snapshot.operations + 1,
        wins=snapshot.wins + (1 if outcome == "WIN" else 0),
        losses=snapshot.losses + (1 if outcome == "LOSS" else 0),
        profit=snapshot.profit + float(profit),
    )


def reset_snapshot(snapshot: CycleSnapshot) -> CycleSnapshot:
    return CycleSnapshot(operations=0, wins=0, losses=0, profit=0.0)

__all__ = ["CycleSnapshot", "apply_outcome", "reset_snapshot"]
