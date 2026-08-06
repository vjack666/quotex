"""Orquestador del Edificio de Contratación: única autoridad de decisión."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .hypothesis import Evidence, Floor, FLOOR_INDEX, Hypothesis, HypothesisStatus
from .watchers import WATCHERS, BaseWatcher


class Orchestrator:
    def __init__(self) -> None:
        self._watchers = {w.floor: w for w in WATCHERS}

    def evaluate(self, hypothesis: Hypothesis, features: Dict[str, Any]) -> Dict[str, Any]:
        current = hypothesis.current_floor
        watcher = self._watchers.get(current)
        if watcher is None:
            return {"decision": "NO", "new_floor": current, "reason": "Sin vigilante para el piso actual"}

        decision = watcher.evaluate(hypothesis, features)
        watcher.record(hypothesis, decision, score=self._score_for(decision), evidence_text=self._evidence_text(decision, features))

        if decision == "SÍ" and current != Floor.LISTO:
            next_floor = Floor.ordered()[FLOOR_INDEX[current] + 1]
            hypothesis.advance(next_floor)
            return {"decision": "SUBIR_PISO", "new_floor": next_floor, "reason": f"Avance a {next_floor}"}

        if decision == "NO":
            hypothesis.invalidate()
            return {"decision": "EXPULSAR", "new_floor": current, "reason": "Vigilante respondió NO"}

        if decision == "RETROCEDE":
            prev = Floor.ordered()[max(FLOOR_INDEX[current] - 1, 0)]
            hypothesis.retrocede(prev)
            return {"decision": "BAJAR_PISO", "new_floor": prev, "reason": f"Retroceso a {prev}"}

        return {"decision": "MANTENER_PISO", "new_floor": current, "reason": "Vigilante respondió SIGUE"}

    def contract_if_ready(self, hypothesis: Hypothesis) -> Optional[Dict[str, Any]]:
        if hypothesis.current_floor != Floor.LISTO:
            return None
        if hypothesis.status == HypothesisStatus.CONTRATADA:
            return None
        hypothesis.contract()
        return {"decision": "CONTRATAR", "direction": hypothesis.direction, "asset": hypothesis.asset}

    def _score_for(self, decision: str) -> float:
        return {"SÍ": 0.1, "SIGUE": 0.05, "RETROCEDE": -0.1, "NO": -0.2}.get(decision, 0.0)

    def _evidence_text(self, decision: str, features: Dict[str, Any]) -> str:
        if decision == "SÍ":
            return "Condición cumplida con suficiente fuerza"
        if decision == "NO":
            return "Condición no cumplida"
        if decision == "RETROCEDE":
            return "Condición cumplida pero perdió calidad"
        return "Condición cumplida pero insuficiente para avanzar"


from .hypothesis import FLOOR_INDEX
