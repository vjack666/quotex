"""Pure session gating decisions for execution.

The policy intentionally knows nothing about the broker or bot. The existing
executor remains responsible for invoking Massaniello and applying side
 effects until the integration is regression-covered.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SessionGate:
    blocked: bool
    reason: str = ""


def gate_massaniello(*, enabled: bool, complete: bool = False, failed: bool = False,
                     timeout: bool = False, exhausted: bool = False,
                     can_enter: bool = True) -> SessionGate:
    if not enabled:
        return SessionGate(False)
    if complete:
        return SessionGate(True, "sesión Massaniello cumplida (3 ITM)")
    if failed:
        return SessionGate(True, "sesión Massaniello fallida")
    if timeout:
        return SessionGate(True, "sesión Massaniello expirada")
    if exhausted:
        return SessionGate(True, "sesión Massaniello sin operaciones restantes")
    if not can_enter:
        return SessionGate(True, "sesión Massaniello no admite más entradas")
    return SessionGate(False)

__all__ = ["SessionGate", "gate_massaniello"]
