"""Tests T2/T3 — CsvSource y BlackBoxSource (R2.3, R2.4, R6.1-R6.3, R7.1, R7.2)."""
import json
import sqlite3

import pytest

from marketfeed.base import KIND_CANDLE_CLOSED, KIND_FEED_GAP
from marketfeed.sources import BlackBoxSource, CsvSource

BASE = 1785072000  # epoch alineado a minuto


# ---------------------------------------------------------------- T2: CSV

def _write_csv(path, rows):
    header = "asset,timeframe,ts,open,high,low,close\n"
    path.write_text(header + "".join(rows), encoding="utf-8")


def test_csv_dedup_gap_and_report(tmp_path):
    """(a)+(d): 6 velas M1 con 2 duplicados y un hueco de 3 velas.

    Velas en ts BASE+0,60,120, luego hueco (faltan 180,240,300), sigue 360,420.
    5 velas únicas + 2 filas duplicadas = 7 filas. Gap: desde=120, hasta=360.
    """
    p = tmp_path / "data.csv"
    rows = []
    for off in (0, 60, 120, 360, 420):
        ts = BASE + off
        rows.append(f"EURUSD,60,{ts},1.0,1.1,0.9,1.05\n")
    # duplicados exactos de ts BASE y BASE+60
    rows.append(f"EURUSD,60,{BASE},1.0,1.1,0.9,1.05\n")
    rows.append(f"EURUSD,60,{BASE + 60},1.0,1.1,0.9,1.05\n")
    _write_csv(p, rows)

    src = CsvSource(str(p))
    events = list(src.iter_events())

    candles = [e for e in events if e.kind == KIND_CANDLE_CLOSED]
    gaps = [e for e in events if e.kind == KIND_FEED_GAP]
    assert len(candles) == 5
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.payload == {"ts_desde": BASE + 120, "ts_hasta": BASE + 360}
    assert gap.source == "REPLAY:csv:data.csv"
    # orden por ts no-decreciente
    ts_list = [e.ts for e in events]
    assert ts_list == sorted(ts_list)
    # (d) quality_report cuadra
    assert src.quality_report() == {
        "served": 5,
        "discarded_dup": 2,
        "discarded_contaminated": 0,
        "gaps": 1,
    }


def test_csv_invalid_schema_raises(tmp_path):
    """(b) R7.2: esquema inválido → ValueError explícito."""
    p = tmp_path / "bad.csv"
    p.write_text("asset,ts,close\nEURUSD,123,1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="esquema inválido"):
        list(CsvSource(str(p)).iter_events())


# ---------------------------------------------------------------- T3: BlackBox

def _make_db(path, snapshots):
    con = sqlite3.connect(str(path))
    con.execute(
        "CREATE TABLE scan_candidates ("
        "id INTEGER PRIMARY KEY, ts REAL, asset TEXT,"
        "candles_1m TEXT, candles_5m TEXT, candles_15m TEXT)"
    )
    for i, (ts, asset, c1m) in enumerate(snapshots):
        con.execute(
            "INSERT INTO scan_candidates (id, ts, asset, candles_1m, candles_5m, candles_15m)"
            " VALUES (?,?,?,?,?,?)",
            (i + 1, ts, asset, json.dumps(c1m), None, None),
        )
    con.commit()
    con.close()


def _c(ts, close):
    return {"ts": ts, "o": close, "h": close, "l": close, "c": close}


def test_blackbox_dedup_contamination_and_report(tmp_path):
    """(c)+(d): 2 snapshots con velas repetidas + 1 contaminada (10x mediana).

    Snapshot 1: velas ts BASE+0..240 (5 velas, cierre 1.0).
    Snapshot 2: velas ts BASE+60..300 → 4 repetidas (60..240) + 1 nueva (300),
                y una vela contaminada en BASE+360 con cierre 10.0 (10x mediana 1.0).
    Únicas: 7 (0..360) → 1 contaminada descartada → 6 servidas, sin hueco
    (360-300=60 ≤ tf... la contaminada se descarta, dejando 0..300 contiguas → 0 gaps).
    """
    db = tmp_path / "black_box_strat_2026-07-26.db"
    snap1 = [_c(BASE + off, 1.0) for off in (0, 60, 120, 180, 240)]
    snap2 = [_c(BASE + off, 1.0) for off in (60, 120, 180, 240, 300)] + [_c(BASE + 360, 10.0)]
    _make_db(db, [(BASE + 240.5, "EURUSD_otc", snap1), (BASE + 300.5, "EURUSD_otc", snap2)])

    src = BlackBoxSource(str(db))
    events = list(src.iter_events())

    candles = [e for e in events if e.kind == KIND_CANDLE_CLOSED]
    gaps = [e for e in events if e.kind == KIND_FEED_GAP]
    assert len(candles) == 6  # 11 filas - 4 dup - 1 contaminada
    assert len(gaps) == 0
    assert all(e.source == "REPLAY:blackbox:2026-07-26" for e in events)
    assert [e.ts for e in candles] == [BASE + off for off in (0, 60, 120, 180, 240, 300)]
    assert all(e.payload["timeframe"] == 60 for e in candles)
    assert src.quality_report() == {
        "served": 6,
        "discarded_dup": 4,
        "discarded_contaminated": 1,
        "gaps": 0,
    }


def test_blackbox_gap_emitted(tmp_path):
    """R2.4 en blackbox: hueco M1 > 1 período → FEED_GAP con desde/hasta."""
    db = tmp_path / "black_box_strat_2026-07-26.db"
    snap = [_c(BASE, 1.0), _c(BASE + 60, 1.0), _c(BASE + 300, 1.0)]
    _make_db(db, [(BASE + 300.5, "USDJPY_otc", snap)])

    src = BlackBoxSource(str(db))
    events = list(src.iter_events())
    gaps = [e for e in events if e.kind == KIND_FEED_GAP]
    assert len(gaps) == 1
    assert gaps[0].payload == {"ts_desde": BASE + 60, "ts_hasta": BASE + 300}
    rep = src.quality_report()
    assert rep["served"] == 3 and rep["gaps"] == 1
