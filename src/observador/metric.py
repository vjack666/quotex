"""Metric — valor medido según PTM v3 (ningún número desnudo).

Todo valor que el Observador registra lleva: raw (lo medido), normalized
(0-1 comparable), confidence (0-1, cuánto fiarse) y formula_version (qué
instrumento lo midió). docs/PTM_V3.md — CONGELADO.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    raw: float
    normalized: float
    confidence: float
    formula_version: str

    def __post_init__(self) -> None:
        for name in ("raw", "normalized", "confidence"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(f"Metric.{name} debe ser numérico, no {v!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Metric.confidence fuera de [0,1]: {self.confidence}")
        if not 0.0 <= self.normalized <= 1.0:
            raise ValueError(f"Metric.normalized fuera de [0,1]: {self.normalized}")
        if not self.formula_version or not isinstance(self.formula_version, str):
            raise ValueError("Metric.formula_version es obligatorio (PTM v3)")
