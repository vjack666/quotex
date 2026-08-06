"""Tests para el Administrador del Edificio."""
from __future__ import annotations

import pytest

from strategy_lab.building_administrator import BuildingAdministrator
from strategy_lab.hypothesis import Floor, Hypothesis, HypothesisStatus


def make_hypothesis(confidence: float = 0.5, urgency: str = "LOW") -> Hypothesis:
    h = Hypothesis(hypothesis_id="H1", asset="EURUSD", direction="CALL")
    h.confidence = confidence
    h.urgency = urgency
    return h


class TestBuildingAdministrator:
    def test_admit_rejects_low_confidence(self) -> None:
        admin = BuildingAdministrator()
        h = make_hypothesis(confidence=0.2)
        result = admin.admit(h)
        assert result["decision"] == "RECHAZAR"

    def test_admit_accepts_and_sets_priority(self) -> None:
        admin = BuildingAdministrator()
        h = make_hypothesis(confidence=0.8)
        result = admin.admit(h)
        assert result["decision"] == "ADMITIR"
        assert h.priority_score == 0.8
        assert h.attention_level == "HIGH"

    def test_prioritize_sorted_by_score(self) -> None:
        admin = BuildingAdministrator()
        h1 = make_hypothesis(confidence=0.6)
        h1.hypothesis_id = "H1"
        h2 = make_hypothesis(confidence=0.9)
        h2.hypothesis_id = "H2"
        admin.admit(h1)
        admin.admit(h2)
        ordered = admin.prioritize()
        assert ordered[0].hypothesis_id == "H2"

    def test_archive_if_stale_when_not_ready(self) -> None:
        admin = BuildingAdministrator(max_active=10, archive_cycles=3)
        h = make_hypothesis()
        h.current_floor = Floor.CONFIRMANDO_CRUCE
        h.history.append(None)  # dummy event
        h.history.append(None)
        result = admin.archive_if_stale(h)
        assert result["decision"] == "MANTENER"

    def test_archive_if_stale_when_ready(self) -> None:
        admin = BuildingAdministrator(max_active=10, archive_cycles=3)
        h = make_hypothesis()
        h.current_floor = Floor.LISTO
        result = admin.archive_if_stale(h)
        assert result["decision"] == "MANTENER"
        assert result["reason"] == "LISTO"

    def test_archive_lowest_priority_when_full(self) -> None:
        admin = BuildingAdministrator(max_active=2, archive_cycles=3)
        h1 = make_hypothesis(confidence=0.9)
        h1.hypothesis_id = "H1"
        h2 = make_hypothesis(confidence=0.8)
        h2.hypothesis_id = "H2"
        h3 = make_hypothesis(confidence=0.5)
        h3.hypothesis_id = "H3"
        admin.admit(h1)
        admin.admit(h2)
        admin.admit(h3)
        assert len(admin.active) <= 2
        active_ids = {h.hypothesis_id for h in admin.active}
        for h in [h1, h2, h3]:
            if h.hypothesis_id in active_ids:
                assert h.status == HypothesisStatus.VIVA
            else:
                assert h.status == HypothesisStatus.ARCHIVADA
