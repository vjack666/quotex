"""Gate de fabrica — punto de integracion con el Edificio (R3/R4/R5/R8).

El Edificio invoca `assemble_from_tools()` en el momento de CONTRATADO. Cada
herramienta registrada activa emite su Evidence (segun su piso y direccion del
BuildingCard) y el Ensamblador+Inspector producen la decision final.

NO reescribe la logica de pisos P1->P2->P3 del edificio_contratacion.py: es una
capa que se anade al final del embudo. El Edificio sigue decidiendo el ascenso;
la fabrica decide la ORDEN.
"""
from __future__ import annotations

from typing import List, Optional

from .evidence import Evidence
from .registry import Tool, active_tools
from .assembler import Decision, assemble


# Mapa de la direccion interna del Edificio ("call"/"put") a Evidence ("LONG"/"SHORT")
_DIR = {"call": "LONG", "put": "SHORT"}


def build_evidences(card_direction: Optional[str],
                    tools: Optional[List[Tool]] = None) -> List[Evidence]:
    """Cada herramienta activa emite su Evidence segun la direccion del activo.

    `card_direction` es "call" | "put" | None (del BuildingCard.direction).
    """
    if card_direction is None:
        return []
    ev_dir = _DIR.get(card_direction.lower())
    if ev_dir is None:
        return []
    tools = tools or active_tools()
    evidences: List[Evidence] = []
    for t in tools:
        # La herramienta apoya la direccion del edificio con su confianza propia
        # (derivada de su WR pooled: cuanto mayor WR, mayor confianza relativa).
        conf = max(0.0, min(1.0, (t.wr_pooled - 50.0) / 20.0))  # 50%->0, 70%->1
        evidences.append(t.emit(ev_dir, strength=conf, confidence=conf))
    return evidences


def assemble_from_tools(card_direction: Optional[str],
                        tools: Optional[List[Tool]] = None) -> Decision:
    """Punto de entrada para el Edificio en CONTRATADO (R4/R5/R8)."""
    evidences = build_evidences(card_direction, tools)
    decision = assemble(evidences)
    return decision
