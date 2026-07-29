"""Tests del agente vivo (aprendizaje en tiempo real, determinista)."""

import json
import os
import sqlite3
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import agent_live as al  # noqa: E402


def _make_db(path, rows):
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute(
        """CREATE TABLE scan_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT, direction TEXT, order_result TEXT,
            stoch_m15 TEXT, stoch_m5 TEXT, stoch_m1 TEXT
        )"""
    )
    for r in rows:
        cur.execute(
            "INSERT INTO scan_candidates (asset, direction, order_result, stoch_m15, stoch_m5, stoch_m1) "
            "VALUES (?,?,?,?,?,?)",
            (
                r["asset"],
                r["direction"],
                r["outcome"],
                json.dumps(r.get("m15", {})),
                json.dumps(r.get("m5", {})),
                json.dumps(r.get("m1", {})),
            ),
        )
    con.commit()
    con.close()


@pytest.fixture
def fake_db(tmp_path, monkeypatch):
    db = tmp_path / "black_box_strat-2026-07-24.db"
    rows = [
        # CALL con M15 bajando (hipotesis de Ruben)
        {"asset": "EUR/USD", "direction": "CALL", "outcome": "WIN",
         "m15": {"k": 30, "k_prev": 45, "trend": "bajando", "zone": "SOBREVENTA"}},
        {"asset": "GBP/USD", "direction": "CALL", "outcome": "LOSS",
         "m15": {"k": 25, "k_prev": 40, "trend": "bajando", "zone": "SOBREVENTA"}},
        {"asset": "USD/JPY", "direction": "PUT", "outcome": "WIN",
         "m15": {"k": 80, "k_prev": 60, "trend": "subiendo", "zone": "SOBRECOMPRA"}},
        {"asset": "AUD/USD", "direction": "CALL", "outcome": "WIN",
         "m15": {"k": 20, "k_prev": 50, "trend": "bajando", "zone": "SOBREVENTA"}},
    ]
    _make_db(db, rows)
    monkeypatch.setattr(al, "_db_paths", lambda: [str(db)])
    mem = tmp_path / "live_memory.json"
    monkeypatch.setattr(al, "MEMORY_PATH", str(mem))
    return db, mem


def test_load_new_trades(fake_db):
    db, _ = fake_db
    trades, max_id = al.load_new_trades(0)
    assert len(trades) == 4
    assert max_id == 4
    assert trades[0]["direction"] == "CALL"
    # sin stoch_m5/m1 los dicts quedan vacios
    assert trades[0]["stoch"]["m15"]["trend"] == "bajando"


def test_poll_once_learns_and_asks(fake_db):
    db, mem = fake_db
    res = al.poll_once()
    assert res["new_trades"] == 4
    assert res["n_total"] == 4
    assert res["winrate"] == 0.75  # 3 WIN de 4

    data = json.loads(mem.read_text(encoding="utf-8"))
    # celdas direction x TF x tendencia
    assert any(k.startswith("CALL|") and "M15:bajando" in k for k in data["cells"])
    cell = [k for k in data["cells"] if "CALL|" in k and "M15:bajando" in k][0]
    assert data["cells"][cell]["n"] == 3
    # auto-preguntas generadas
    assert len(data["last_questions"]) == 4
    q0 = data["last_questions"][0]
    assert any("¿Por que" in qa["q"] for qa in q0["qa"])
    assert any("¿Que debo mejorar" in qa["q"] for qa in q0["qa"])


def test_poll_once_incremental(fake_db):
    db, mem = fake_db
    al.poll_once()  # aprende 4
    # agregar 1 trade mas y volver a hacer poll
    con = sqlite3.connect(str(db))
    con.execute(
        "INSERT INTO scan_candidates (asset, direction, order_result, stoch_m15) "
        "VALUES (?,?,?,?)",
        ("CAD/JPY", "PUT", "LOSS", json.dumps({"k": 70, "k_prev": 55, "trend": "subiendo", "zone": "SOBRECOMPRA"})),
    )
    con.commit()
    con.close()
    res = al.poll_once()
    assert res["new_trades"] == 1
    assert res["n_total"] == 5
    data = json.loads(mem.read_text(encoding="utf-8"))
    assert data["last_seen_id"] == 5


def test_render_report(fake_db):
    db, mem = fake_db
    al.poll_once()
    data = json.loads(mem.read_text(encoding="utf-8"))
    rep = al.render_report(data)
    assert "Agente VIVO" in rep
    assert "auto-preguntas" in rep or "auto-pregunta" in rep
    assert "WIN" in rep or "winrate" in rep.lower()


def test_on_trade_resolved_does_not_crash(fake_db):
    db, mem = fake_db
    # no debe lanzar aunque se llame con order_id vacio
    al.on_trade_resolved("", "")
    data = json.loads(mem.read_text(encoding="utf-8"))
    assert data["n_total"] == 4
