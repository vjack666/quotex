"""State-free asset entry/blacklist policies."""
from __future__ import annotations
import time


def is_blacklisted(blacklist: dict[str, float], asset: str, now: float | None = None) -> bool:
    now = time.time() if now is None else float(now)
    until = blacklist.get(asset)
    return until is not None and now < float(until)


def register_loss(streaks: dict[str, int], blacklist: dict[str, float], asset: str,
                  limit: int, duration_min: float, now: float | None = None) -> int:
    if limit <= 0:
        return streaks.get(asset, 0)
    now = time.time() if now is None else float(now)
    streak = int(streaks.get(asset, 0)) + 1
    streaks[asset] = streak
    if streak >= limit:
        blacklist[asset] = now + float(duration_min) * 60.0
    return streak


def register_win(streaks: dict[str, int], asset: str) -> None:
    streaks[asset] = 0

__all__ = ["is_blacklisted", "register_loss", "register_win"]
