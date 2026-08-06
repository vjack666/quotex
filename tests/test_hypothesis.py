"""Tests para el motor de hipótesis, vigilantes y orquestador."""
from __future__ import annotations

from typing import Any, Dict

import pytest

from strategy_lab.hypothesis import Evidence, Floor, FLOOR_INDEX, Hypothesis, HypothesisStatus
from strategy_lab.orchestrator import Orchestrator
from strategy_lab.watchers import (
    Floor0Observer,
    Floor1Candidate,
    Floor2EnPoi,
    Floor3RespeandoPoi,
    Floor4EnCruce,
    Floor5ConfirmandoCruce,
    Floor6ConfirmandoVela,
    WATCHERS,
)


def make_hypothesis() -> Hypothesis:
    return Hypothesis(hypothesis_id="H1", asset="EURUSD", direction="CALL")


class TestHypothesis:
    def test_create_hypothesis_defaults(self) -> None:
        h = make_hypothesis()
        assert h.status == HypothesisStatus.VIVA
        assert h.current_floor == Floor.OBSERVANDO
        assert h.confidence == 0.0
        assert h.history == []
        assert h.evidence == {}

    def test_advance_sequential(self) -> None:
        h = make_hypothesis()
        h.advance(Floor.CANDIDATO)
        assert h.current_floor == Floor.CANDIDATO

    def test_advance_non_sequential_raises(self) -> None:
        h = make_hypothesis()
        with pytest.raises(ValueError):
            h.advance(Floor.EN_POI)

    def test_retrocede_lowers_floor(self) -> None:
        h = make_hypothesis()
        h.advance(Floor.CANDIDATO)
        h.advance(Floor.EN_POI)
        h.retrocede(Floor.CANDIDATO)
        assert h.current_floor == Floor.CANDIDATO
        assert any("Retrocedió" in o for o in h.observations)

    def test_retrocede_invalid_raises(self) -> None:
        h = make_hypothesis()
        with pytest.raises(ValueError):
            h.retrocede(Floor.OBSERVANDO)

    def test_invalidate_sets_status(self) -> None:
        h = make_hypothesis()
        h.invalidate()
        assert h.status == HypothesisStatus.INVALIDADA

    def test_contract_sets_contracted(self) -> None:
        h = make_hypothesis()
        h.contract()
        assert h.status == HypothesisStatus.CONTRATADA

    def test_archive_sets_archived(self) -> None:
        h = make_hypothesis()
        h.archive()
        assert h.status == HypothesisStatus.ARCHIVADA

    def test_add_evidence_updates_history(self) -> None:
        h = make_hypothesis()
        h.add_evidence(Floor.OBSERVANDO, 0.1, "Impulso moderado", {"impulse_ok": True})
        assert Floor.OBSERVANDO in h.evidence
        assert len(h.history) == 1
        assert h.evidence[Floor.OBSERVANDO].score == 0.1


class TestFloorOrder:
    def test_ordered_floors(self) -> None:
        assert Floor.ordered()[0] == Floor.OBSERVANDO
        assert Floor.ordered()[-1] == Floor.LISTO
        assert len(Floor.ordered()) == 8

    def test_floor_index_consistency(self) -> None:
        for i, f in enumerate(Floor.ordered()):
            assert FLOOR_INDEX[f] == i


class TestWatchers:
    def test_all_watchers_have_floor_and_question(self) -> None:
        for w in WATCHERS:
            assert w.floor is not None
            assert w.question
            assert w.mission

    def test_floor0_requires_impulse(self) -> None:
        w = Floor0Observer()
        h = make_hypothesis()
        assert w.evaluate(h, {"impulse_ok": False}) == "NO"
        assert w.evaluate(h, {"impulse_ok": True}) == "SÍ"

    def test_floor2_poi_quality(self) -> None:
        w = Floor2EnPoi()
        h = make_hypothesis()
        assert w.evaluate(h, {"at_poi": True, "body_n": 0.1, "brake_ratio": 0.5}) == "SÍ"
        assert w.evaluate(h, {"at_poi": True, "body_n": 0.5, "brake_ratio": 0.9}) == "SIGUE"

    def test_floor3_poi_respected_cycles(self) -> None:
        w = Floor3RespeandoPoi()
        h = make_hypothesis()
        assert w.evaluate(h, {"poi_respected": False}) == "NO"
        assert w.evaluate(h, {"poi_respected": True, "poi_respected_cycles": 0}) == "SIGUE"
        assert w.evaluate(h, {"poi_respected": True, "poi_respected_cycles": 1}) == "SÍ"

    def test_floor5_separation_quality(self) -> None:
        w = Floor5ConfirmandoCruce()
        h = make_hypothesis()
        assert w.evaluate(h, {"kd_dist": 1.5}) == "NO"
        assert w.evaluate(h, {"kd_dist": 2.0}) == "SIGUE"
        assert w.evaluate(h, {"kd_dist": 5.0}) == "SÍ"


class TestOrchestrator:
    def setup_method(self) -> None:
        self.orchestrator = Orchestrator()
        self.h = make_hypothesis()

    def test_evaluate_advances_floor(self) -> None:
        result = self.orchestrator.evaluate(self.h, {"impulse_ok": True})
        assert result["decision"] == "SUBIR_PISO"
        assert self.h.current_floor == Floor.CANDIDATO

    def test_evaluate_no_expulsa(self) -> None:
        result = self.orchestrator.evaluate(self.h, {"impulse_ok": False})
        assert result["decision"] == "EXPULSAR"
        assert self.h.status == HypothesisStatus.INVALIDADA

    def test_contract_when_ready(self) -> None:
        for floor in Floor.ordered()[:-1]:
            self.orchestrator.evaluate(self.h, self._features_for_floor(floor))
        assert self.h.current_floor == Floor.LISTO
        result = self.orchestrator.contract_if_ready(self.h)
        assert result["decision"] == "CONTRATAR"
        assert self.h.status == HypothesisStatus.CONTRATADA

    def test_contract_already_contracted_returns_none(self) -> None:
        self.h.contract()
        result = self.orchestrator.contract_if_ready(self.h)
        assert result is None

    def test_retrocede_behavior(self) -> None:
        self.orchestrator.evaluate(self.h, {"impulse_ok": True})
        self.orchestrator.evaluate(self.h, {"swing_confirmed": False})
        assert self.h.current_floor == Floor.CANDIDATO
        assert self.h.status == HypothesisStatus.INVALIDADA

    def test_evaluate_record_evidence(self) -> None:
        self.orchestrator.evaluate(self.h, {"impulse_ok": True})
        assert Floor.OBSERVANDO in self.h.evidence
        assert len(self.h.history) == 1

    def _features_for_floor(self, floor: Floor) -> Dict[str, Any]:
        return {
            "impulse_ok": True,
            "swing_confirmed": True,
            "at_poi": True,
            "body_n": 0.1,
            "brake_ratio": 0.5,
            "poi_respected": True,
            "poi_respected_cycles": 1,
            "cross_clean_confirmed": True,
            "kd_dist": 5.0,
            "hammer_confirmed": True,
        }
