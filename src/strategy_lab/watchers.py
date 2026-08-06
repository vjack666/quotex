"""Vigilantes por piso del Edificio de Contratación."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .hypothesis import Evidence, Floor, Hypothesis


class BaseWatcher(ABC):
    floor: Floor = Floor.OBSERVANDO
    mission: str = ""
    question: str = ""

    def evaluate(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> str:
        if not self._condition_met(hypothesis, features):
            return "NO"
        if not self._sufficient_to_advance(hypothesis, features):
            return "SIGUE"
        return "SÍ"

    def record(self, hypothesis: Hypothesis, decision: str, score: float, evidence_text: str, features: Optional[Dict[str, Any]] = None) -> None:
        hypothesis.add_evidence(self.floor, score=score, evidence=f"{self.mission}: {evidence_text} ({decision})", features=features)
        hypothesis.last_decision = decision

    @abstractmethod
    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        raise NotImplementedError


class Floor0Observer(BaseWatcher):
    floor = Floor.OBSERVANDO
    mission = "Detectar activos que merecen atención"
    question = "¿Hay algo que mirar?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("impulse_ok", False))

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return True


class Floor1Candidate(BaseWatcher):
    floor = Floor.CANDIDATO
    mission = "Confirmar swing válido"
    question = "¿Hay un swing válido?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("swing_confirmed", False))

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return True


class Floor2EnPoi(BaseWatcher):
    floor = Floor.EN_POI
    mission = "Verificar llegada a área de interés"
    question = "¿Llegó a un área de interés?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("at_poi", False))

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        body_n = features.get("body_n")
        brake_ratio = features.get("brake_ratio")
        return bool(body_n is not None and brake_ratio is not None and body_n < 0.35 and brake_ratio < 0.7)


class Floor3RespeandoPoi(BaseWatcher):
    floor = Floor.RESPEANDO_POI
    mission = "Confirmar respeto del POI"
    question = "¿Lo está respetando?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("poi_respected", False))

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("poi_respected_cycles", 0) >= 1)


class Floor4EnCruce(BaseWatcher):
    floor = Floor.EN_CRUCE
    mission = "Detectar cruce estocástico en zona extrema"
    question = "¿Existe intención de giro?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("cross_clean_confirmed", False))

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return True


class Floor5ConfirmandoCruce(BaseWatcher):
    floor = Floor.CONFIRMANDO_CRUCE
    mission = "Validar calidad del cruce"
    question = "¿Ese giro tiene calidad?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        kd_dist = features.get("kd_dist")
        return bool(kd_dist is not None and kd_dist >= 2.0)

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        kd_dist = features.get("kd_dist")
        return bool(kd_dist is not None and kd_dist >= 5.0)


class Floor6ConfirmandoVela(BaseWatcher):
    floor = Floor.CONFIRMANDO_VELA
    mission = "Esperar confirmación de vela"
    question = "¿El precio confirmó esa intención?"

    def _condition_met(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return bool(features.get("hammer_confirmed", False))

    def _sufficient_to_advance(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> bool:
        return True


WATCHERS = [
    Floor0Observer(),
    Floor1Candidate(),
    Floor2EnPoi(),
    Floor3RespeandoPoi(),
    Floor4EnCruce(),
    Floor5ConfirmandoCruce(),
    Floor6ConfirmandoVela(),
]

