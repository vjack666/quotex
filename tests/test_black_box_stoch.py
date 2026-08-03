"""Verifica que el black box registra stoch_m5 + filter_funnel para auditoría post-mortem.

Req: auditoría después de operar debe incluir info del estocástico M5 y el
funnel de filtros por capa (para auditar asimetría fresca vs promovida y
posible look-ahead de M1). Ver issue discusión 2026-07-19.
"""
import json
import sqlite3

import pytest

from black_box_recorder import get_black_box, BLACK_BOX_DB


@pytest.fixture
def bb(tmp_path, monkeypatch):
    # Aísla la DB de caja negra para no tocar la del día.
    import black_box_recorder as bbr

    monkeypatch.setattr(bbr, "DB_DIR", tmp_path)
    monkeypatch.setattr(bbr, "BLACK_BOX_DB", tmp_path / "black_box_strat_test.db")
    recorder = bbr.BlackBoxRecorder()
    yield recorder


def test_record_candidate_stores_stoch_m5_and_funnel(bb):
    stoch_m5 = {"k": 12.3, "d": 18.1, "exhausted": True}
    funnel = [
        "fractal_m5:ok",
        "m15_context_detect:downtrend",
        "maturing_wait:ok",
        "m15_recheck_align:fail",
        "m5_exhaustion:ok",
    ]
    cid = bb.record_candidate(
        1,
        "STRAT-F",
        {
            "asset": "TESTSTOCH_otc",
            "direction": "CALL",
            "score": 71.0,
            "payout": 85,
            "decision": "ACCEPTED",
            "stoch_m15": {"k": 40.0, "d": 42.0, "zone": "Z3", "action": "BOOST"},
            "stoch_m5": stoch_m5,
            "filter_funnel": funnel,
            "duration_sec": 900,
        },
    )
    assert cid > 0
    # Lectura directa para confirmar que las columnas nuevas se persistieron.
    con = sqlite3.connect(bb.db_path)
    row = con.execute(
        "SELECT stoch_m5, filter_funnel FROM scan_candidates WHERE id = ?",
        (cid,),
    ).fetchone()
    con.close()
    assert row is not None
    got_m5 = json.loads(row[0]) if row[0] else None
    got_funnel = json.loads(row[1]) if row[1] else None
    assert got_m5 == stoch_m5
    assert got_funnel == funnel


def test_record_candidate_null_stoch_m5_when_fresh_route(bb):
    # Ruta fresca: stoch_m5 ausente -> se guarda "{}" (cero NULL, no se inventa).
    cid = bb.record_candidate(
        1,
        "STRAT-F",
        {
            "asset": "TESTSTOCH_otc",
            "direction": "PUT",
            "score": 60.0,
            "payout": 80,
            "decision": "REJECTED_STOCH",
            "stoch_m15": {"k": 88.0, "action": "VETO"},
            "stoch_m5": None,
            "filter_funnel": [
                "fractal_m5:ok",
                "m15_context:uptrend",
                "stoch_m15_hard:VETO",
                "m1_reject:ok",
            ],
            "duration_sec": 900,
        },
    )
    con = sqlite3.connect(bb.db_path)
    row = con.execute(
        "SELECT stoch_m5, filter_funnel FROM scan_candidates WHERE id = ?",
        (cid,),
    ).fetchone()
    con.close()
    assert row[0] == "{}"  # cero NULL: ausente -> "{}", nunca None
    assert json.loads(row[1])[2] == "stoch_m15_hard:VETO"


def test_record_candidate_agent_tag_distinguishes_who(bb):
    """Etiqueta para saber quien lanzo la orden: BOT | WATCHDOG | HUMAN."""
    cid = bb.record_candidate(
        1, "STRAT-F",
        {
            "asset": "TESTSTOCH_otc",
            "direction": "PUT",
            "score": 100.0,
            "payout": 85,
            "decision": "ACCEPTED",
            "decision_reason": "WATCHDOG:agotamiento_confirmado:ruptura:martillo",
            "stoch_m15": {"k": 88.0, "d": 70.0},
            "stoch_m5": {"k": 40.0, "d": 55.0, "cruce": "bajista"},
            "agent_tag": "WATCHDOG",
            "order_id": "watchdog-test-001",
            "duration_sec": 300,
        },
    )
    con = sqlite3.connect(bb.db_path)
    tag = con.execute(
        "SELECT agent_tag FROM scan_candidates WHERE id = ?", (cid,)
    ).fetchone()[0]
    con.close()
    assert tag == "WATCHDOG"
    # Y el resultado se resuelve con la misma etiqueta intacta
    bb.record_order_result("watchdog-test-001", "WIN", 0.85)
    con = sqlite3.connect(bb.db_path)
    res = con.execute(
        "SELECT order_result, agent_tag FROM scan_candidates WHERE order_id = ?",
        ("watchdog-test-001",),
    ).fetchone()
    con.close()
    assert res[0] == "WIN"
    assert res[1] == "WATCHDOG"


def test_record_candidate_persists_direction_source(tmp_path, monkeypatch):
    """Persistencia de la telemetría Fase A: origen de la dirección M1/M15/''.

    Usamos una DB aislada porque la DB de producción no se contamina con fixtures.
    """
    db = tmp_path / "test_direction_source.db"
    monkeypatch.setattr(
        "black_box_recorder.BLACK_BOX_DB",
        db,
    )
    bb = __import__("black_box_recorder").BlackBoxRecorder()
    for source in ("M1", "M15", ""):
        bb.record_candidate(
            1,
            "EDIFICIO",
            {
                "asset": "TESTDS_otc",
                "direction": "CALL" if source != "PUT" else "PUT",
                "score": 60.0,
                "payout": 80,
                "decision": "ACCEPTED",
                "decision_reason": f"TEST:{source}",
                "stoch_m15": {"k": 40.0, "d": 42.0},
                "direction_source": source if source else None,
            },
        )
    con = sqlite3.connect(bb.db_path)
    rows = con.execute(
        "SELECT id, direction_source FROM scan_candidates WHERE asset = 'TESTDS_otc' ORDER BY id ASC"
    ).fetchall()
    con.close()
    assert len(rows) == 3
    assert rows[0][1] == "M1"
    assert rows[1][1] == "M15"
    assert rows[2][1] is None
