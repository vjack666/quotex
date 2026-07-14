"""Tests de la caja negra STRAT-F (Fase 1): esquema extendido + grabación.

Usa una DB temporal para no tocar la DB del día. Verifica que los campos
nuevos (candles_15m, session_id, stoch_m15, entry/exit_price, candles_post,
loss_reason, improvement_hint, stoch_contradicts) se escriben y leen.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import black_box_recorder as bbr


def _make_tmp_recorder(monkeypatch):
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test_black_box.db"
    rec = bbr.BlackBoxRecorder.__new__(bbr.BlackBoxRecorder)
    rec.db_path = db_path
    rec.log_path = Path(tmp) / "test.jsonl"
    rec._init_db()
    return rec


def test_record_and_update_full_roundtrip():
    import types

    # Construir recorder con DB temporal sin tocar la real.
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test_black_box.db"
    rec = bbr.BlackBoxRecorder.__new__(bbr.BlackBoxRecorder)
    rec.db_path = db_path
    rec.log_path = Path(tmp) / "test.jsonl"
    rec._init_db()

    sid = rec.record_scan_start("STRAT-F", 1, {"market_state": "ranging", "volatility_atr": 0.5})
    cid = rec.record_candidate(sid, "STRAT-F", {
        "asset": "USDCOP_otc", "direction": "put", "score": 63.6, "payout": 87,
        "decision": "ACCEPTED", "decision_reason": "filtros OK", "reject_reason": "",
        "strategy_details": {"f1": 1},
        "candles_1m": [{"c": 1}], "candles_5m": [{"c": 2}],
        "candles_15m": [{"c": 3, "high": 4}],
        "session_id": "S1",
        "stoch_m15": {"k": 84, "d": 80, "estado": "SOBRECOMPRA"},
    })
    rec.update_candidate(
        cid, order_result="WIN", profit=7.8, entry_price=3400.5, exit_price=3410.2,
        candles_post=[{"c": 4}], stoch_m15={"k": 20, "d": 22, "estado": "SOBREVENTA"},
        stoch_contradicts=0, loss_reason=None, improvement_hint="ok",
    )

    import sqlite3
    con = sqlite3.connect(rec.db_path)
    row = con.execute(
        "SELECT candles_15m, session_id, stoch_m15, order_result, profit, "
        "entry_price, exit_price, candles_post, loss_reason, improvement_hint, "
        "stoch_contradicts FROM scan_candidates WHERE id=?",
        (cid,),
    ).fetchone()
    con.close()

    assert row[0] is not None, "candles_15m debe guardarse"
    assert row[1] == "S1"
    assert row[2] is not None
    assert row[3] == "WIN"
    assert row[4] == 7.8
    assert row[5] == 3400.5
    assert row[6] == 3410.2
    assert row[7] is not None
    assert row[9] == "ok"
    assert row[10] == 0


def test_migration_idempotent_on_existing_db():
    """Correr _init_db dos veces no rompe ni duplica columnas."""
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test_black_box.db"
    rec = bbr.BlackBoxRecorder.__new__(bbr.BlackBoxRecorder)
    rec.db_path = db_path
    rec.log_path = Path(tmp) / "test.jsonl"
    rec._init_db()
    rec._init_db()  # segunda vez: debe ser idempotente
    import sqlite3
    con = sqlite3.connect(rec.db_path)
    cols = [str(r[1]).lower() for r in con.execute("PRAGMA table_info(scan_candidates)").fetchall()]
    con.close()
    for needed in ["candles_15m", "candles_post", "entry_price", "exit_price",
                   "session_id", "stoch_m15", "stoch_contradicts",
                   "loss_reason", "improvement_hint"]:
        assert needed in cols, f"falta columna {needed}"
