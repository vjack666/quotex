"""Feature 41 — verificación de piezas operativas (sin red al broker).

Cubre R2/R3 (barrera REAL), R5 (monto Massaniello), R7 (snapshot PISO_1),
R8 (retención infinita de caja negra).
"""
import os
import sys
import tempfile

import pytest

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, os.path.abspath(SRC))

import config
from black_box_recorder import BlackBoxRecorder
from edificio_contratacion import EdificioContratacion


# ── R8: retención infinita ──────────────────────────────────────────
def test_retention_infinite_and_no_cleanup(tmp_path):
    rec = BlackBoxRecorder.__new__(BlackBoxRecorder)
    rec.RETENTION_DAYS = 0  # Feature 41 R8
    old_file = tmp_path / "old.jsonl"
    old_file.write_text("x")
    rec._cleanup_old_files()
    assert old_file.exists(), "RETENTION_DAYS=0 NO debe borrar archivos"


# ── R7: snapshot PISO_1 ─────────────────────────────────────────────
def test_edificio_records_p1_snapshot(tmp_path, monkeypatch):
    db = tmp_path / "blackbox_test.db"
    rec = BlackBoxRecorder()
    rec.db_path = str(db)
    rec._init_db()

    calls = {"n": 0}

    class SpyBB:
        def record_piso1_snapshot(self, *a, **k):
            calls["n"] += 1
            return rec.record_piso1_snapshot(*a, **k)

    spy = SpyBB()
    monkeypatch.setattr("edificio_contratacion.get_black_box", lambda: spy)
    monkeypatch.setattr("black_box_recorder.get_black_box", lambda: spy)

    ed = EdificioContratacion()
    ed.reset()
    candles_1m = [{"time": i, "close": 1.0 + i * 0.01} for i in range(10)]
    ed.evaluate(asset="UTEST", direction="CALL", payout=85, payout_ok=True,
                candles_1m=candles_1m)

    assert calls["n"] >= 1, "evaluate debe llamar record_piso1_snapshot al entrar a PISO_1"

    import sqlite3, json
    con = sqlite3.connect(str(db))
    rows = con.execute(
        "SELECT decision, candles_1m FROM scan_candidates WHERE decision='PISO1_SNAPSHOT'"
    ).fetchall()
    con.close()
    assert rows, "debe existir un snapshot PISO1_SNAPSHOT"
    n = len(json.loads(rows[0][1])) if rows[0][1] else 0
    assert n == 10, "debe guardar las 10 velas 1m"


# ── R2/R3: barrera REAL ────────────────────────────────────────────
def test_allow_real_blocks_real_account(monkeypatch):
    import asyncio
    from edificio_executor import execute_contratados

    monkeypatch.setattr(config, "EDIFICIO_ALLOW_REAL", False)

    ev = type("E", (), {"asset": "X", "direction": "CALL", "timestamp": 0.0,
                        "card": None, "tries": 0, "order_id": None, "order_ref": None,
                        "order_status": ""})()

    class FakeEd2:
        def pop_contratados(self):
            return [ev]
        def requeue(self, e):
            pass
        def get_card(self, a):
            return None

    class FakeBot:
        trades = {}
        client = None

    sent = asyncio.run(execute_contratados(FakeBot(), account_type="REAL"))
    assert sent == 0, "cuenta REAL debe bloquearse con ALLOW_REAL=False"


# ── R5: monto Massaniello ──────────────────────────────────────────
def test_massaniello_stake_used(monkeypatch):
    import asyncio
    from edificio_executor import _send_one, STAKE_MODE

    monkeypatch.setattr(config, "STAKE_MODE", "massaniello")

    class Card:
        payout = 80
        piso = 4  # CONTRATADO
        order_status = ""
        reason = ""

    class Ev:
        asset = "M"
        direction = "CALL"
        card = Card()
        timestamp = 0.0

    class Mgr:
        def next_stake(self, payout):
            return (3.5, "A1")

    class FakeEd:
        def register_sent(self, *a, **k):
            return None
        def requeue(self, e):
            return None
        def get_card(self, a):
            return None

    class Bot:
        massaniello = Mgr()

    calls = {}

    async def fake_place(**kw):
        calls["amount"] = kw["amount"]
        calls["account_type"] = kw.get("account_type")
        return (True, "id1", "ok", 1, "")

    import edificio_executor as ee
    monkeypatch.setattr(ee, "place_order", fake_place)

    ok, _ = asyncio.run(_send_one(Bot(), None, FakeEd(), Ev(),
                                  account_type="PRACTICE", amount=1.0,
                                  duration=60, max_tries=1))
    assert ok is True
    assert abs(calls["amount"] - 3.5) < 1e-9, "debe usar monto Massaniello 3.5"
