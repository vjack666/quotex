"""Tipos compartidos del Discovery Engine (CONTRATO). No importa nada del bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Law:
    id: str
    name: str
    conditions: str
    probability: float
    confidence: str
    markets: tuple[str, ...]
    sources: tuple[str, ...]
    timeframes: tuple[str, ...]
    cases_studied: int
    state: str = "EXPERIMENTAL"
    discovery_version: str = "discovery_v1"
    script_ref: str = ""
    # Campos opcionales de soporte para el reporte R7 (no rompen la firma del contrato).
    p_value: float = 0.0
    ci: tuple[float, float] = (0.0, 0.0)

    VALID_STATES = ("EXPERIMENTAL", "VALIDADA", "FUERTE", "UNIVERSAL", "OBSOLETA")


@dataclass(frozen=True)
class Episode:
    episode_id: int
    asset: str
    market: str
    source: str
    ts_open: float
    ts_close: float
    state_final: str
    evolution: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LawRelation:
    from_law: str
    to_law: str
    relation_type: str
    strength: float
    discovery_version: str = "discovery_v1"

    VALID_TYPES = ("refuerza", "contradice", "requiere")
