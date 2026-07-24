"""Tests de distribución activa del Experience Engine en el scorer (T8/T9).

Verifica que al evaluar un candidato, el engine EMPUJA su memoria a la IA
(lectura: query_similar -> win rate observado) y que NUNCA escribe en la
memoria (las IAs solo leen).
"""
from __future__ import annotations

import pytest

import entry_scorer
from experience_engine import ExperienceMemory
from experience_schema import MarketExperience


class _MockEntry:
    """Candidato mínimo para probar solo la capa de distribución."""
    def __init__(self, asset, direction, stoch_zone):
        self.asset = asset
        self.direction = direction
        self.stoch_m15 = {"estado": stoch_zone}
        self.score = 80.0
        self.score_breakdown = {}


def _seed_mem(tmp_path) -> ExperienceMemory:
    mem = ExperienceMemory(root=tmp_path / "mem")
    for i in range(10):
        mem.record(MarketExperience(
            ts=1784920000 + i, asset="EURUSD_otc", tf="M15",
            contexto_previo={"stoch_m15": {"zone": "NEUTRO"}},
            evento={"tipo": "entrada", "direccion": "CALL"},
            evolucion={"pips_recorridos": 18.0},
            resultado={"decision": "WIN"},
            consecuencias={},
        ))
    return mem


def test_distrib_reads_memory_and_adjusts(monkeypatch, tmp_path):
    mem = _seed_mem(tmp_path)
    monkeypatch.setattr(entry_scorer, "_get_experience_memory", lambda: mem)
    monkeypatch.setattr(entry_scorer, "OBSERVATION_ENABLED", True)

    entry = _MockEntry("EURUSD_otc", "CALL", "NEUTRO")
    before_count = mem.count()

    entry_scorer._apply_experience_distrib(entry)

    # WR observado de experiencias similares (10 WIN de 10)
    assert entry.score_breakdown["experience_win_rate"] == 1.0
    assert entry.score_breakdown["experience_n"] == 10
    # Ajuste aplicado (WR 1.0 -> +8 pts sobre score 80)
    assert entry.score_breakdown["experience_adj"] == 8.0
    assert entry.score == 88.0
    # La memoria NO creció: las IAs solo leen
    assert mem.count() == before_count


def test_distrib_disabled_when_flag_off(monkeypatch, tmp_path):
    mem = _seed_mem(tmp_path)
    monkeypatch.setattr(entry_scorer, "_get_experience_memory", lambda: mem)
    monkeypatch.setattr(entry_scorer, "OBSERVATION_ENABLED", False)

    entry = _MockEntry("EURUSD_otc", "CALL", "NEUTRO")
    entry_scorer._apply_experience_distrib(entry)

    assert "experience_win_rate" not in entry.score_breakdown
    assert entry.score == 80.0  # intacto


def test_distrib_no_adjust_with_insufficient_sample(monkeypatch, tmp_path):
    mem = ExperienceMemory(root=tmp_path / "mem")
    mem.record(MarketExperience(
        ts=1784920000, asset="EURUSD_otc", tf="M15",
        contexto_previo={"stoch_m15": {"zone": "NEUTRO"}},
        evento={"tipo": "entrada", "direccion": "CALL"},
        resultado={"decision": "WIN"}, consecuencias={},
    ))
    monkeypatch.setattr(entry_scorer, "_get_experience_memory", lambda: mem)
    monkeypatch.setattr(entry_scorer, "OBSERVATION_ENABLED", True)

    entry = _MockEntry("EURUSD_otc", "CALL", "NEUTRO")
    entry_scorer._apply_experience_distrib(entry)

    assert "experience_win_rate" not in entry.score_breakdown  # muestra < 5
    assert entry.score == 80.0
