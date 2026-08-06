"""Administrador del Edificio de Contratación: admite, prioriza y archiva hipótesis."""
from __future__ import annotations

from typing import Any, Dict, List

from .hypothesis import Evidence, Floor, Hypothesis, HypothesisStatus


class BuildingAdministrator:
    def __init__(self, max_active: int = 20, archive_cycles: int = 20) -> None:
        self.max_active = max_active
        self.archive_cycles = archive_cycles
        self.active: List[Hypothesis] = []

    def admit(self, hypothesis: Hypothesis, min_confidence: float = 0.3) -> Dict[str, Any]:
        if hypothesis.confidence < min_confidence:
            return {"decision": "RECHAZAR", "reason": "Confianza insuficiente"}
        if len(self.active) >= self.max_active:
            self._archive_lowest_priority()
        self.active.append(hypothesis)
        hypothesis.priority_score = self._priority_score(hypothesis)
        hypothesis.attention_level = self._attention_level(hypothesis.priority_score)
        return {"decision": "ADMITIR", "priority_score": hypothesis.priority_score, "attention_level": hypothesis.attention_level}

    def prioritize(self) -> List[Hypothesis]:
        return sorted(self.active, key=lambda h: h.priority_score, reverse=True)

    def archive_if_stale(self, hypothesis: Hypothesis) -> Dict[str, Any]:
        if hypothesis.current_floor == Floor.LISTO:
            return {"decision": "MANTENER", "reason": "LISTO"}
        wait_cycles = len(hypothesis.history)
        if wait_cycles >= self.archive_cycles:
            hypothesis.status = HypothesisStatus.ARCHIVADA
            self.active = [h for h in self.active if h.hypothesis_id != hypothesis.hypothesis_id]
            return {"decision": "ARCHIVAR", "reason": f"Sin evidencia nueva en {wait_cycles} ciclos"}
        return {"decision": "MANTENER", "reason": f"{wait_cycles}/{self.archive_cycles} ciclos"}

    def _priority_score(self, hypothesis: Hypothesis) -> float:
        base = hypothesis.confidence
        urgency = {"HIGH": 0.1, "MEDIUM": 0.05, "LOW": 0.0}.get(hypothesis.urgency, 0.0)
        return min(1.0, max(0.0, base + urgency))

    def _attention_level(self, score: float) -> str:
        if score >= 0.75:
            return "HIGH"
        if score >= 0.5:
            return "MEDIUM"
        return "LOW"

    def _archive_lowest_priority(self) -> None:
        if not self.active:
            return
        lowest = min(self.active, key=lambda h: h.priority_score)
        lowest.status = HypothesisStatus.ARCHIVADA
        self.active = [h for h in self.active if h.hypothesis_id != lowest.hypothesis_id]
