"""Modelo de datos del nuevo HUB STRAT-F.

Un solo estado: aceptadas vs rechazadas, con la razón de cada rechazo.
Reemplaza los modelos orientados a STRAT-A (CandidateData / HubState /
MasanielloState) que vivían en hub_models.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class StratFRow:
    """Señal STRAT-F que pasó todos los filtros."""

    asset: str
    direction: str          # "call" | "put"
    strength: int           # 0-100
    payout: int            # %
    ctx: str               # range | uptrend | downtrend | broken
    event: str             # fractal_up | fractal_down | none


@dataclass
class StratFReject:
    """Activo STRAT-F descartado, con la razón legible."""

    asset: str
    payout: int
    skip_reason: str       # p.ej. "M1 no rebota (cierra fuera)"


@dataclass
class StratFHubState:
    """Estado completo del panel HUB STRAT-F para un ciclo."""

    accepted: List[StratFRow] = field(default_factory=list)
    rejected: List[StratFReject] = field(default_factory=list)
    total_assets: int = 0
    filtered_count: int = 0
    cycle: int = 0
    timestamp: float = 0.0

    @property
    def total(self) -> int:
        return len(self.accepted) + len(self.rejected)

    @property
    def accept_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return len(self.accepted) / self.total
