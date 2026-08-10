"""Evidence — contrato de evidencia de una herramienta (R2).

Una HERRAMIENTA del Edificio emite Evidence. La evidencia describe lo que la
herramienta VE (direccion, fuerza, confianza, etapa del piso), pero NUNCA
contiene un campo de orden (BUY/SELL). La orden la produce el ENSAMBLADOR (R4),
no la herramienta. Es la regla de fabrica: las herramientas fabrican piezas,
el ensamblador arma el auto.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Direcciones permitidas en evidencia (sin BUY/SELL)
Direction = str  # "LONG" | "SHORT" | "NONE"
Stage = str       # "P1" | "P2" | "P3" | "CONTRATADO"


@dataclass(frozen=True)
class Evidence:
    """Veredicto de una herramienta sobre un activo en un piso del edificio.

    Campos (R2):
      direction : "LONG" | "SHORT" | "NONE"  -- lo que la herramienta ve
      strength  : 0..1                        -- magnitud del senal
      confidence: 0..1                        -- certeza de la herramienta
      stage     : "P1"|"P2"|"P3"|"CONTRATADO" -- piso que emite la evidencia
      tool      : nombre de la herramienta origen (para trazabilidad R8)
      note      : texto libre opcional
    """
    direction: Direction
    strength: float
    confidence: float
    stage: Stage
    tool: str
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if self.direction not in ("LONG", "SHORT", "NONE"):
            raise ValueError(f"direction invalida: {self.direction}")
        if self.stage not in ("P1", "P2", "P3", "CONTRATADO"):
            raise ValueError(f"stage invalido: {self.stage}")
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"strength fuera de rango: {self.strength}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence fuera de rango: {self.confidence}")

    @property
    def is_conflicting(self) -> bool:
        """Una herramienta con direccion opuesta y confianza alta es conflicto (R5)."""
        return self.direction != "NONE" and self.confidence >= 0.5
