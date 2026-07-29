"""Tests minimos del pipeline auditor de rechazos (offline).

(a) record_candidate acepta 'band' y lo escribe en scan_candidates.
(b) stage_extract cuenta bien sobre un DB sintetico: 1 REJECTED_STRAT_F joven
    + 1 SHADOW_PROMOTED del mismo asset/direction/band -> 1 madurado exacto.
"""
import os
import sqlite3
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "src"), os.path.join(_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import audit_rechazos as AR  # noqa: E402


# --- (a) record_candidate escribe band --------------------------------------
def _make_min_schema(path: str) -> None:
    """Crea el schema minimo de scan_candidates (sin band, para probar ALTER)."""
    con = sqlite3.connect(path)
    con.execute("""
        CREATE TABLE scan_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER, ts REAL, strategy TEXT, asset TEXT, direction TEXT,
            score REAL, confidence REAL, payout INTEGER, decision TEXT,
            decision_reason TEXT, reject_reason TEXT, strategy_details TEXT,
            candles_1m TEXT, candles_5m TEXT, candles_15m TEXT, session_id TEXT,
            stoch_m15 TEXT, stoch_m5 TEXT, filter_funnel TEXT, order_id TEXT,
            duration_sec INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, ts_iso TEXT,
            strategy TEXT, scan_number INTEGER, market_state TEXT, volatility_atr REAL
        )
    """)
    con.commit()
    con.close()


def test_record_candidate_escribe_band(tmp_path):
    from black_box_recorder import BlackBoxRecorder

    db = str(tmp_path / "bb.db")
    _make_min_schema(db)
    rec = BlackBoxRecorder.__new__(BlackBoxRecorder)  # sin __init__ (evita DB global)
    rec.db_path = db
    rec.log_path = str(tmp_path / "bb.log")
    cid = rec.record_candidate(1, "STRAT-F", {
        "asset": "EUR/USD_otc", "direction": "CALL", "score": 55.0,
        "decision": "REJECTED_STRAT_F",
        "reject_reason": "zona muy joven (2 < 3 velas M5)",
        "band": 1.23456789,
    })
    assert cid > 0
    con = sqlite3.connect(db)
    cols = [r[1] for r in con.execute("PRAGMA table_info(scan_candidates)")]
    assert "band" in cols  # ALTER idempotente creo la columna
    band = con.execute("SELECT band FROM scan_candidates WHERE id=?", (cid,)).fetchone()[0]
    con.close()
    assert band == pytest.approx(1.23456789)


def test_record_candidate_band_none(tmp_path):
    from black_box_recorder import BlackBoxRecorder

    db = str(tmp_path / "bb2.db")
    _make_min_schema(db)
    rec = BlackBoxRecorder.__new__(BlackBoxRecorder)
    rec.db_path = db
    rec.log_path = str(tmp_path / "bb2.log")
    cid = rec.record_candidate(1, "STRAT-F", {
        "asset": "GBP/USD_otc", "direction": "PUT", "decision": "REJECTED_STOCH",
    })
    con = sqlite3.connect(db)
    band = con.execute("SELECT band FROM scan_candidates WHERE id=?", (cid,)).fetchone()[0]
    con.close()
    assert band is None


# --- (b) stage_extract cruza rechazo->promocion -----------------------------
def _synthetic_rows():
    band = 1.10500
    return [
        # rechazo 'zona muy joven'
        {"id": 1, "ts": 1000.0, "asset": "EUR/USD_otc", "direction": "CALL",
         "score": 55.0, "decision": "REJECTED_STRAT_F",
         "reject_reason": "zona muy joven (2 < 3 velas M5)",
         "strategy_details": None, "stoch_m15": None, "stoch_m5": None,
         "stoch_m1": None, "candles_15m": None, "band": band},
        # promocion posterior, mismo asset/direction/band -> madura EXACTO
        {"id": 2, "ts": 1000.0 + 600, "asset": "EUR/USD_otc", "direction": "CALL",
         "score": 60.0, "decision": "SHADOW_PROMOTED",
         "reject_reason": "", "strategy_details": None, "stoch_m15": None,
         "stoch_m5": None, "stoch_m1": None, "candles_15m": None, "band": band},
        # rechazo por stoch, sin promocion -> no madura
        {"id": 3, "ts": 2000.0, "asset": "GBP/USD_otc", "direction": "PUT",
         "score": 50.0, "decision": "REJECTED_STOCH",
         "reject_reason": "stoch_extreme_against", "strategy_details": None,
         "stoch_m15": None, "stoch_m5": None, "stoch_m1": None,
         "candles_15m": None, "band": 1.30000},
    ]


def test_extract_cuenta_maduracion_exacta():
    res = AR.stage_extract(_synthetic_rows(), window_min=90)
    assert res["total_rejects"] == 2
    assert res["total_promos"] == 1
    young = res["by_reason"]["zona muy joven (2 < 3 velas M5)"]
    assert young["total"] == 1
    assert young["young"] == 1
    assert young["matured"] == 1
    assert young["matured_exact_band"] == 1
    stoch = res["by_reason"]["stoch_extreme_against"]
    assert stoch["matured"] == 0
    assert len(res["matched"]) == 1
    assert res["matched"][0]["exact_band"] is True


def test_extract_band_distinto_no_cruza():
    rows = _synthetic_rows()
    rows[1]["band"] = 9.99999  # promocion con band distinto
    res = AR.stage_extract(rows, window_min=90)
    young = res["by_reason"]["zona muy joven (2 < 3 velas M5)"]
    assert young["matured"] == 0  # band presente pero distinto -> no es el mismo nivel


def test_extract_fuera_de_ventana_no_cruza():
    rows = _synthetic_rows()
    rows[1]["ts"] = 1000.0 + 90 * 60 + 1  # justo fuera de la ventana +90min
    res = AR.stage_extract(rows, window_min=90)
    young = res["by_reason"]["zona muy joven (2 < 3 velas M5)"]
    assert young["matured"] == 0
