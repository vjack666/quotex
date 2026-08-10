"""Edificio de Contratacion — Fabrica de Herramientas.

Subpaquete de utilidades de la fabrica del Edificio (feature 40, SDD
fabrica_herramientas_edificio). NO es un segundo edificio: alimenta los
pisos P1->P2->P3 de `edificio_contratacion.py` con herramientas que emiten
EVIDENCIA, no ordenes (R2 del contrato).

Estructura (orden para administracion y venta del producto):
  evidence.py   -> dataclass Evidence (R2): direction/strength/confidence/stage
  registry.py    -> dataclass Tool (R1) + loader del catalogo
  catalog.json   -> herramientas ya medidas en el laboratorio (legible)
  inspector.py   -> INSPECTOR (R5): frena si direccion opuesta con confianza alta
  assembler.py   -> ENSAMBLADOR (R4): unico que produce BUY/SELL/NO_TRADE
  gate.py        -> punto de integracion con el Edificio en CONTRATADO (R3/R4/R5/R8)
  README.md      -> mapa de la carpeta para el nuevo dueno

Ver specs/fabrica_herramientas_edificio/ para el contrato completo (R0-R16).
"""
from __future__ import annotations

from .evidence import Evidence
from .registry import Tool, load_catalog, get_tool, active_tools
from .inspector import inspect
from .assembler import Decision, assemble
from .gate import build_evidences, assemble_from_tools

__all__ = [
    "Evidence", "Tool", "load_catalog", "get_tool", "active_tools",
    "inspect", "Decision", "assemble", "build_evidences", "assemble_from_tools",
]
