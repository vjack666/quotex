"""Registry — identidad de herramienta (R1) y loader del catalogo.

Toda herramienta promovida al Edificio se registra con su EXP de origen, su WR
pooled, su n, su veredicto Charter y el dominio donde obtuvo evidencia. El
catalogo vive en `catalog.json` (legible para el nuevo dueno del producto).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .evidence import Evidence, Direction, Stage

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")


@dataclass(frozen=True)
class Tool:
    """Cedula de identidad de una herramienta del Edificio (R1)."""
    name: str
    exp_ref: str                 # EXP-XXX de origen
    wr_pooled: float             # win rate ponderada medida
    n: int                       # n combinado de la evidencia
    charter_verdict: str         # veredicto del Laboratory Charter
    domain: str                  # REAL | OTC | BOTH
    stage: Stage                 # piso del edificio que alimenta
    active: bool = True          # False = descartada (ej. cruce_limpio)
    note: str = ""

    def emit(self, direction: Direction, strength: float, confidence: float,
             note: Optional[str] = None) -> Evidence:
        """La herramienta emite EVIDENCIA (nunca orden)."""
        return Evidence(
            direction=direction, strength=strength, confidence=confidence,
            stage=self.stage, tool=self.name, note=note or self.note,
        )


def load_catalog(path: str = _CATALOG_PATH) -> List[Tool]:
    """Carga el catalogo de herramientas desde JSON (R1)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    tools: List[Tool] = []
    for item in raw.get("tools", []):
        tools.append(Tool(
            name=item["name"],
            exp_ref=item["exp_ref"],
            wr_pooled=float(item["wr_pooled"]),
            n=int(item["n"]),
            charter_verdict=item["charter_verdict"],
            domain=item["domain"],
            stage=item["stage"],
            active=bool(item.get("active", True)),
            note=item.get("note", ""),
        ))
    return tools


def get_tool(name: str, path: str = _CATALOG_PATH) -> Optional[Tool]:
    """Devuelve una herramienta por nombre, o None."""
    for t in load_catalog(path):
        if t.name == name:
            return t
    return None


def active_tools(path: str = _CATALOG_PATH) -> List[Tool]:
    """Solo herramientas activas (R1)."""
    return [t for t in load_catalog(path) if t.active]
