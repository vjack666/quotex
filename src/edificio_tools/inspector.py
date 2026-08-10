"""Inspector — guard de conflictos (R5).

El inspector precede a la contratacion. Si dos o mas herramientas activas emiten
direction opuesta con confidence >= 0.5, la oportunidad es CONFLICTO y el
ensamblador debe producir NO_TRADE. Es el control de calidad de la fabica.
"""
from __future__ import annotations

from typing import List

from .evidence import Evidence


def inspect(evidences: List[Evidence]) -> tuple[bool, str]:
    """Devuelve (hay_conflicto, razon).

    Conflicto = al menos dos evidencias activas con direction opuesta y
    confidence >= 0.5 (R5).
    """
    conflicting = [e for e in evidences if e.is_conflicting]
    longs = [e for e in conflicting if e.direction == "LONG"]
    shorts = [e for e in conflicting if e.direction == "SHORT"]
    if longs and shorts:
        names = [e.tool for e in longs] + [e.tool for e in shorts]
        return True, f"conflicto direccion opuesta entre {names}"
    return False, ""
