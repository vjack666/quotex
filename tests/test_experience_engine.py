"""Tests del Experience Engine (Feature 27).

Cubre: round-trip del arco (T2), memoria única con dos IAs que solo leen (T5),
modo activo distribuye a IAs (T9), y seed OFFLINE desde DB sintética + validación
de que el contexto correlaciona con win rate (T12/T13).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from experience_engine import ExperienceEngine, ExperienceMemory
from experience_schema import MarketExperience


# ─────────────────────────────────────────────────────────────────────────────
#  T2 — round-trip del arco
# ─────────────────────────────────────────────────────────────────────────────
def test_experience_roundtrip():
    exp = MarketExperience(
        ts=1784924820,
        asset="EURUSD_otc",
        tf="M15",
        contexto_previo={"stoch_m15": {"zone": "NEUTRO", "k": 31.25}},
        evento={"tipo": "entrada", "direccion": "CALL", "nivel": 1.12450},
        evolucion={"pips_recorridos": 18.0},
        resultado={"decision": "WIN", "pips_netos": 18.0},
        consecuencias={"loss_reason": None},
        raw={"candles_15m": [{"c": 1.12450}]},
    )
    d = exp.to_dict()
    back = MarketExperience.from_dict(d)
    assert back.ts == exp.ts
    assert back.asset == exp.asset
    assert back.evento == exp.evento
    assert back.resultado == exp.resultado
    assert back.raw == exp.raw
    assert back.fingerprint() == exp.fingerprint()
    assert back.is_closed() is True


# ─────────────────────────────────────────────────────────────────────────────
#  T5 — dos IAs leen la MISMA memoria; ninguna escribe
# ─────────────────────────────────────────────────────────────────────────────
def test_two_ias_read_only(tmp_path):
    mem = ExperienceMemory(root=tmp_path / "mem")
    exp = MarketExperience(
        ts=1784924820, asset="EURUSD_otc", tf="M15",
        evento={"tipo": "entrada", "direccion": "CALL"},
        resultado={"decision": "WIN"},
    )
    mem.record(exp)
    size_before = sum(1 for _ in (tmp_path / "mem").glob("*.jsonl"))

    # Dos IAs consultan (solo lectura)
    got1 = mem.query_similar({"asset": "EURUSD_otc"})
    got2 = mem.query_similar({"asset": "EURUSD_otc", "direction": "CALL"})
    assert len(got1) == 1 and len(got2) == 1

    size_after = sum(1 for _ in (tmp_path / "mem").glob("*.jsonl"))
    assert size_after == size_before, "una IA escribió en la memoria"
    # y la memoria no creció en conteo de experiencias
    assert mem.count() == 1


# ─────────────────────────────────────────────────────────────────────────────
#  T9 — modo activo: inyectar experiencia similar dispara distribución a la IA
# ─────────────────────────────────────────────────────────────────────────────
def test_active_distribution(tmp_path):
    eng = ExperienceEngine(memory=ExperienceMemory(root=tmp_path / "mem"))

    # Sembrar una experiencia histórica similar
    eng.memory.record(MarketExperience(
        ts=1784920000, asset="EURUSD_otc", tf="M15",
        evento={"tipo": "entrada", "direccion": "CALL"},
        resultado={"decision": "WIN"},
    ))

    received = {}
    def ia_handler(exp: MarketExperience, similars):
        received["exp"] = exp
        received["similars"] = similars
        return 0.9  # Confidence Score

    eng.register_ia(ia_handler)

    # Adquirir experiencia en vivo similar
    new_exp = MarketExperience(
        ts=1784924820, asset="EURUSD_otc", tf="M15",
        evento={"tipo": "entrada", "direccion": "CALL"},
        resultado={"decision": "WIN"},
    )
    resp = eng.acquire(new_exp)

    assert received["exp"] is new_exp
    assert len(received["similars"]) >= 1  # encontró la histórica
    assert resp["ia_0"] == 0.9


# ─────────────────────────────────────────────────────────────────────────────
#  T12/T13 — seed OFFLINE desde DB sintética + validación de correlación
# ─────────────────────────────────────────────────────────────────────────────
def _write_small_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    con.execute(
        """CREATE TABLE scan_candidates (
            id INTEGER PRIMARY KEY, ts REAL, asset TEXT, direction TEXT,
            score REAL, payout REAL, decision TEXT, strategy_details TEXT,
            candles_1m TEXT, candles_5m TEXT, candles_15m TEXT,
            order_result TEXT, profit REAL, entry_price REAL, exit_price REAL,
            loss_reason TEXT, improvement_hint TEXT, duration_sec REAL,
            stoch_m15 TEXT, stoch_m5 TEXT, stoch_m1 TEXT
        )"""
    )
    rows = []
    base = 1784920000.0
    # 12 CALL ganadores en estado NEUTRO, 12 CALL perdedores en estado EXTREMO
    for i in range(12):
        rows.append((
            base + i, "EURUSD_otc", "CALL", 70.0, 90, "ACCEPTED",
            json.dumps({"ctx": "range", "event": "fractal_down", "pattern": "x"}),
            json.dumps([{"c": 1.12450}]), json.dumps([]), json.dumps([{"c": 1.12450}]),
            "WIN", 1.0, 1.12450, 1.12630, None, None, 900,
            json.dumps({"estado": "NEUTRO", "k": 30, "d": 35}),
            None, None,
        ))
    for i in range(12):
        rows.append((
            base + 100 + i, "EURUSD_otc", "CALL", 70.0, 90, "ACCEPTED",
            json.dumps({"ctx": "range", "event": "fractal_down", "pattern": "x"}),
            json.dumps([{"c": 1.12450}]), json.dumps([]), json.dumps([{"c": 1.12450}]),
            "LOSS", -1.0, 1.12450, 1.12300, "break", None, 900,
            json.dumps({"estado": "EXTREMO", "k": 90, "d": 85}),
            None, None,
        ))
    con.executemany(
        """INSERT INTO scan_candidates (
            ts, asset, direction, score, payout, decision, strategy_details,
            candles_1m, candles_5m, candles_15m, order_result, profit,
            entry_price, exit_price, loss_reason, improvement_hint, duration_sec,
            stoch_m15, stoch_m5, stoch_m1
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    con.commit()
    con.close()


def test_seed_offline_and_validation(tmp_path):
    db = tmp_path / "bb_test.db"
    _write_small_db(db)

    mem = ExperienceMemory(root=tmp_path / "mem")
    # Reusar la lógica del script de seed (import estático del módulo)
    import scripts.seed_experience_memory as seed

    n = seed.seed_db(db, mem)
    assert n == 24, f"se esperaban 24 experiencias, got {n}"

    exps = mem.all_experiences()
    closed = [e for e in exps if e.is_closed()]
    assert len(closed) == 24

    # Validación (R6/R8): agrupar por estado stoch -> WR debe diferir
    groups = {}
    for e in closed:
        key = e.contexto_previo.get("stoch_m15", {}).get("zone")
        groups.setdefault(key, []).append(e)
    neutro = groups.get("NEUTRO", [])
    extremo = groups.get("EXTREMO", [])
    wr_neutro = sum(1 for e in neutro if e.resultado.get("decision") == "WIN") / len(neutro)
    wr_extremo = sum(1 for e in extremo if e.resultado.get("decision") == "WIN") / len(extremo) if extremo else 0
    assert wr_neutro == 1.0
    assert wr_extremo == 0.0
    assert wr_neutro != wr_extremo  # el contexto SÍ correlaciona con outcome
