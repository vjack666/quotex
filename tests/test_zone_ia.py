"""Tests de la IA de Zonas (Feature 28).

Verifica (RZ8): descubre zonas por clustering sin reglas, emite zone_confidence
coherente (zona WR alto -> confidence alto), y que al evaluar NO escribe en la
memoria (solo lectura).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experience_engine import ExperienceMemory, MarketExperience
from zone_ia import ZoneIA, discover_zones, _zone_confidence_for_level


def _exp(asset, direction, level, win: bool, ts: int):
    return MarketExperience(
        ts=ts,
        asset=asset,
        tf="M5",
        contexto_previo={"stoch_m15_estado": "NEUTRO"},
        evento={"nivel": level, "direction": direction},
        evolucion={},
        resultado={"decision": "WIN" if win else "LOSS", "pips": 15.0 if win else -12.0},
        consecuencias={},
    )


@pytest.fixture
def mem_dir(tmp_path):
    mem = ExperienceMemory(root=tmp_path)
    base_ts = int(datetime.now().timestamp())
    i = 0
    # Zona fuerte en 1.1000: 8 win / 2 loss (WR 0.8) para CALL
    for _ in range(8):
        mem.record(_exp("EURUSD_otc", "call", 1.1000, True, base_ts + i)); i += 1
    for _ in range(2):
        mem.record(_exp("EURUSD_otc", "call", 1.1000, False, base_ts + i)); i += 1
    # Zona débil en 1.2000: 1 win / 9 loss (WR 0.1) para CALL
    mem.record(_exp("EURUSD_otc", "call", 1.2000, True, base_ts + i)); i += 1
    for _ in range(9):
        mem.record(_exp("EURUSD_otc", "call", 1.2000, False, base_ts + i)); i += 1
    # Otra zona en 1.1001 (misma banda de 1.1000 por proximidad)
    mem.record(_exp("EURUSD_otc", "call", 1.1001, True, base_ts + i)); i += 1
    return mem


def test_discover_zones_clusters_without_rules(mem_dir):
    """RZ1/RZ6: agrupa por proximidad de nivel, sin rol hardcoded ni _DECAY_TABLE."""
    zones = discover_zones("EURUSD_otc", mem_dir)
    assert zones, "debe descubrir al menos una zona"
    # La zona fuerte (1.1000) debe aparecer con WR alto
    strong = [z for z in zones if abs(z["nivel"] - 1.1000) < 0.001]
    assert strong, "zona en 1.1000 no descubierta"
    assert strong[0]["win_rate"] >= 0.7
    assert strong[0]["confidence"] >= 0.7
    # Sin etiqueta soporte/resistencia
    assert "soporte" not in strong[0] and "resistencia" not in strong[0]


def test_zone_confidence_coherent(mem_dir):
    """RZ3/RZ8b: zona con WR alto -> confidence alto; zona WR bajo -> confidence bajo."""
    high = _zone_confidence_for_level("EURUSD_otc", "call", 1.1000, mem_dir)
    low = _zone_confidence_for_level("EURUSD_otc", "call", 1.2000, mem_dir)
    assert high is not None and low is not None
    assert high > 0.7
    assert low < 0.25


def test_zone_confidence_insufficient_sample(mem_dir):
    """RZ3: sin muestra suficiente, devuelve None (neutral, no ajusta)."""
    conf = _zone_confidence_for_level("EURUSD_otc", "call", 9.9999, mem_dir)
    assert conf is None


def test_zone_ia_only_reads(mem_dir, tmp_path):
    """RZ5/RZ8d: al evaluar, la memoria NO crece (solo lectura)."""

    class Cand:
        close = 1.1000

    class Entry:
        asset = "EURUSD_otc"
        direction = "CALL"
        entry_price = 1.1000
        candles = [Cand()]

    before = len(list(mem_dir.root.glob("*.jsonl")))
    ZoneIA._mem = mem_dir
    conf = ZoneIA.score(Entry())
    after = len(list(mem_dir.root.glob("*.jsonl")))
    assert conf is not None
    assert after == before, "la IA escribió en la memoria (debe ser solo lectura)"


def test_zone_ia_wall(mem_dir):
    """RZ4b: zona con confidence bajo umbral => is_wall True."""
    class Cand:
        close = 1.2000

    class Entry:
        asset = "EURUSD_otc"
        direction = "CALL"
        entry_price = 1.2000
        candles = [Cand()]

    ZoneIA._mem = mem_dir
    assert ZoneIA.is_wall(Entry()) is True

    class EntryStrong:
        asset = "EURUSD_otc"
        direction = "CALL"
        entry_price = 1.1000
        candles = [Cand()]

    assert ZoneIA.is_wall(EntryStrong) is False
