"""Expediente de hipótesis y máquina de estados del Edificio de Contratación."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HypothesisStatus(str, Enum):
    VIVA = "VIVA"
    MADURANDO = "MADURANDO"
    INVALIDADA = "INVALIDADA"
    CONTRATADA = "CONTRATADA"
    ARCHIVADA = "ARCHIVADA"


class Floor(str, Enum):
    OBSERVANDO = "OBSERVANDO"               # Piso 0
    CANDIDATO = "CANDIDATO"                 # Piso 1
    EN_POI = "EN_POI"                       # Piso 2
    RESPEANDO_POI = "RESPEANDO_POI"         # Piso 3
    EN_CRUCE = "EN_CRUCE"                   # Piso 4
    CONFIRMANDO_CRUCE = "CONFIRMANDO_CRUCE" # Piso 5
    CONFIRMANDO_VELA = "CONFIRMANDO_VELA"   # Piso 6
    LISTO = "LISTO"                         # Piso 7

    @classmethod
    def ordered(cls) -> List["Floor"]:
        return [
            cls.OBSERVANDO,
            cls.CANDIDATO,
            cls.EN_POI,
            cls.RESPEANDO_POI,
            cls.EN_CRUCE,
            cls.CONFIRMANDO_CRUCE,
            cls.CONFIRMANDO_VELA,
            cls.LISTO,
        ]


FLOOR_INDEX: Dict[Floor, int] = {f: i for i, f in enumerate(Floor.ordered())}


@dataclass
class Evidence:
    score: float = 0.0
    evidence: str = ""
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryEvent:
    floor: Floor
    time: str
    event: str
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypothesis:
    hypothesis_id: str
    asset: str
    direction: str  # CALL / PUT
    status: HypothesisStatus = HypothesisStatus.VIVA
    current_floor: Floor = Floor.OBSERVANDO
    ingress_time: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    ingress_reason: str = ""
    priority_score: float = 0.0
    attention_level: str = "LOW"
    urgency: str = "LOW"
    confidence: float = 0.0
    evidence: Dict[Floor, Evidence] = field(default_factory=dict)
    history: List[HistoryEvent] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    features: Dict[str, Any] = field(default_factory=dict)
    last_decision: str = ""

    def add_evidence(self, floor: Floor, score: float, evidence: str, features: Optional[Dict[str, Any]] = None) -> None:
        self.evidence[floor] = Evidence(score=score, evidence=evidence, features=features or {})
        self.history.append(HistoryEvent(floor=floor, time=datetime.utcnow().isoformat() + "Z", event=evidence, features=features or {}))

    def advance(self, new_floor: Floor) -> None:
        if FLOOR_INDEX[new_floor] != FLOOR_INDEX[self.current_floor] + 1:
            raise ValueError(f"Avance secuencial inválido: {self.current_floor} -> {new_floor}")
        self.current_floor = new_floor

    def retrocede(self, new_floor: Floor) -> None:
        if FLOOR_INDEX[new_floor] >= FLOOR_INDEX[self.current_floor]:
            raise ValueError(f"Retroceso inválido: {self.current_floor} -> {new_floor}")
        self.current_floor = new_floor
        self.observations.append(f"Retrocedió a {new_floor}")

    def invalidate(self) -> None:
        self.status = HypothesisStatus.INVALIDADA
        self.observations.append("Hipótesis invalidada")

    def contract(self) -> None:
        self.status = HypothesisStatus.CONTRATADA

    def archive(self) -> None:
        self.status = HypothesisStatus.ARCHIVADA
