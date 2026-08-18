"""Pure session-summary construction for the execution lifecycle."""
from __future__ import annotations
from typing import Any


def build_session_summary(status: dict[str, Any], reason: str) -> dict[str, Any]:
    wins = int(status.get("wins", 0) or 0)
    losses = int(status.get("losses", 0) or 0)
    entries = int(status.get("entries", 0) or 0)
    trades = entries if entries > 0 else wins + losses
    balance = status.get("balance")
    initial = status.get("initial_capital")
    pnl = None
    if balance is not None and initial is not None:
        try:
            pnl = float(balance) - float(initial)
        except (TypeError, ValueError):
            pass
    if status.get("failed"):
        state = "SESSION_FAILED"
    elif status.get("timeout"):
        state = "SESSION_TIMEOUT"
    elif status.get("exhausted"):
        state = "SESSION_EXHAUSTED"
    elif status.get("complete"):
        state = "SESSION_COMPLETE"
    else:
        state = "SESSION_ENDED"
    return {
        "reason": reason,
        "status": state,
        "wins": wins,
        "losses": losses,
        "itm": wins,
        "otm": losses,
        "entries": entries,
        "trades": trades,
        "win_rate": (wins / trades * 100.0) if trades else None,
        "pnl": pnl,
        "balance": balance,
        "initial_capital": initial,
        "elapsed_min": float(status.get("elapsed_min") or 0.0),
        "duration": float(status.get("elapsed_min") or 0.0),
        "failed": bool(status.get("failed")),
        "complete": bool(status.get("complete")),
        "timeout": bool(status.get("timeout")),
        "exhausted": bool(status.get("exhausted")),
        "expected_wins": int(status.get("expected_wins", 0) or 0),
        "operations": int(status.get("operations", 0) or 0),
    }

__all__ = ["build_session_summary"]
