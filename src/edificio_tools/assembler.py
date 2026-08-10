"""Ensamblador — unica maquina que produce la orden (R4).

Combina la evidencia de todas las herramientas activas segun una regla declarada
y congelada, y produce exactamente uno de: BUY, SELL, NO_TRADE.

Regla congelada (mayoria ponderada por confidence, con veto del Inspector R5):
  - Si el Inspector detecta conflicto -> NO_TRADE.
  - Si la mayoria (por confidence) es LONG -> BUY.
  - Si la mayoria es SHORT -> SELL.
  - Si no hay evidencia util o empate -> NO_TRADE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .evidence import Evidence
from .inspector import inspect


@dataclass(frozen=True)
class Decision:
    action: str            # "BUY" | "SELL" | "NO_TRADE"
    direction: Optional[str]  # "LONG" | "SHORT" | None
    strength: float        # 0..1, fuerza agregada
    conflict: bool
    reason: str
    evidences: tuple = ()  # trazabilidad R8


def assemble(evidences: List[Evidence]) -> Decision:
    """Produce la decision final del Edificio (R4 + R5)."""
    evidences = [e for e in evidences if e.direction != "NONE"]
    conflict, reason = inspect(evidences)
    if conflict:
        return Decision("NO_TRADE", None, 0.0, True, reason, tuple(evidences))

    if not evidences:
        return Decision("NO_TRADE", None, 0.0, False,
                        "sin evidencia util", ())

    # Mayoria ponderada por confidence
    score_long = sum(e.confidence for e in evidences if e.direction == "LONG")
    score_short = sum(e.confidence for e in evidences if e.direction == "SHORT")
    total = score_long + score_short
    if total == 0:
        return Decision("NO_TRADE", None, 0.0, False, "confianza cero",
                        tuple(evidences))

    if score_long > score_short:
        direction = "LONG"
        strength = score_long / total
        action = "BUY"
    elif score_short > score_long:
        direction = "SHORT"
        strength = score_short / total
        action = "SELL"
    else:
        return Decision("NO_TRADE", None, 0.0, False, "empate de confianza",
                        tuple(evidences))

    return Decision(action, direction, round(strength, 4), False,
                    f"mayoria {direction} (conf {strength:.2f})", tuple(evidences))
