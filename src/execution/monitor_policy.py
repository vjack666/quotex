"""Pure trade-monitoring timing policy."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MonitorWindow:
    duration_sec: float
    grace_sec: float = 0.0

    @property
    def wait_sec(self) -> float:
        return max(0.0, self.duration_sec + self.grace_sec)


def window(duration_sec: float, grace_sec: float = 0.0) -> MonitorWindow:
    return MonitorWindow(float(duration_sec), float(grace_sec))

__all__ = ["MonitorWindow", "window"]
