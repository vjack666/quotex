"""Verifica que la black-box graba la bandera `extreme_read` (mejora de lectura
de extremo) cuando el scanner la pasa en `data`.

No usa el scanner completo (pesado): prueba el recorder directamente, que es
quien escribe la columna. Esto cierra el ciclo "el bot marca en blackbox cuáles
entaron con la mejora" pedido por el usuario.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_bb(tmp_path, monkeypatch):
    # Redirige el directorio de la caja negra a un temporal
    import black_box_recorder as bbr

    monkeypatch.setattr(bbr, "DB_DIR", tmp_path)
    monkeypatch.setattr(bbr, "BLACK_BOX_DB", tmp_path / "black_box_strat_test.db")
    monkeypatch.setattr(bbr, "LOGS_DIR", tmp_path)
    bb = bbr.BlackBoxRecorder()
    return bb


def test_extreme_read_flag_written(tmp_bb):
    cid = tmp_bb.record_candidate(
        scan_id=1,
        strategy="F",
        data={
            "asset": "EURUSD",
            "direction": "put",
            "score": 80.0,
            "confidence": 0.7,
            "payout": 85,
            "decision": "ACCEPTED",
            "extreme_read": 1,
        },
    )
    assert cid > 0
    con = sqlite3.connect(tmp_bb.db_path)
    row = con.execute(
        "SELECT extreme_read FROM scan_candidates WHERE id=?", (cid,)
    ).fetchone()
    con.close()
    assert row is not None
    assert row[0] == 1  # bandera grabada


def test_extreme_read_default_zero(tmp_bb):
    cid = tmp_bb.record_candidate(
        scan_id=1,
        strategy="F",
        data={
            "asset": "EURUSD",
            "direction": "call",
            "score": 80.0,
            "decision": "ACCEPTED",
        },
    )
    con = sqlite3.connect(tmp_bb.db_path)
    row = con.execute(
        "SELECT extreme_read FROM scan_candidates WHERE id=?", (cid,)
    ).fetchone()
    con.close()
    assert row[0] == 0  # default cuando no se pasa


def test_schema_has_extreme_read_column(tmp_bb):
    con = sqlite3.connect(tmp_bb.db_path)
    cols = [r[1] for r in con.execute("PRAGMA table_info(scan_candidates)")]
    con.close()
    assert "extreme_read" in cols
