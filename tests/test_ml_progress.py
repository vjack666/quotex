"""Verifica que ml_progress respeta la bandera ML_COLLECTION_START.

La bandera debe filtrar el conteo del batch nuevo a trades con
created_at >= la fecha fijada (en scan_candidates, que tiene timestamp).
"""
from __future__ import annotations

import os
import sqlite3
import tempfile

import ml_progress


def _make_db(path: str, rows: list[tuple[str, str]]) -> None:
    """Crea scan_candidates con (order_result, created_at) en `rows`."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE scan_candidates ("
        "id INTEGER PRIMARY KEY, order_result TEXT, strategy TEXT, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    cur.executemany(
        "INSERT INTO scan_candidates (order_result, strategy, created_at) "
        "VALUES (?, 'STRAT-F', ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_bandera_filtra_por_created_at(monkeypatch, tmp_path):
    db = tmp_path / "black_box_strat_test.db"
    _make_db(
        str(db),
        [
            ("WIN", "2026-07-23 10:00:00"),   # antes de la bandera
            ("LOSS", "2026-07-23 18:00:00"),  # despues
            ("WIN", "2026-07-23 20:00:00"),   # despues
            ("LOSS", "2026-07-22 23:00:00"),  # antes (otro dia)
        ],
    )
    monkeypatch.setattr(ml_progress, "ML_COLLECTION_START", "2026-07-23 17:18:39")
    g, b, per = ml_progress.count_resolved([str(db)])
    assert g == 4, f"global debe ser 4, fue {g}"
    assert b == 2, f"batch (desde bandera) debe ser 2, fue {b}"
    assert per[0][2] == 2


def test_sin_bandera_cuenta_todo(monkeypatch, tmp_path):
    db = tmp_path / "black_box_strat_test.db"
    _make_db(
        str(db),
        [
            ("WIN", "2026-07-23 10:00:00"),
            ("LOSS", "2026-07-23 18:00:00"),
        ],
    )
    monkeypatch.setattr(ml_progress, "ML_COLLECTION_START", "")
    g, b, per = ml_progress.count_resolved([str(db)])
    assert g == 2
    assert b == 2  # sin bandera, batch == global


def test_norm_ts_formato_iso(monkeypatch):
    assert ml_progress._norm_ts("2026-07-23T18:00:00.123456") == "2026-07-23 18:00:00"
    assert ml_progress._norm_ts(None) == ""
