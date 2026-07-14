"""Tests de Fase 4 — post-mortem STRAT-F + cierre de candidato en caja negra.

Verifica la lógica de "¿había otra mejor entrada en 1m post-cierre?" y que el
recorder cierra el candidato pendiente con loss_reason/improvement_hint.
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import strat_f_postmortem as pm
import black_box_recorder as bbr
from models import Candle


def _c1m(o, h, l, c):
    return {"ts": 1, "o": o, "h": h, "l": l, "c": c}


def test_loss_with_opposite_reversal_gives_direccion_equivocada():
    # Mockea la detección de patrón post-cierre: aparece reversión PUT fuerte
    # (dirección opuesta a la entrada CALL) => dirección equivocada.
    from candle_patterns import CandleSignal
    before = [_c1m(100, 101, 99, 100), _c1m(100, 101, 99, 100), _c1m(100, 101, 99, 100)]
    after = [_c1m(100, 101, 99, 100), _c1m(100, 102, 98, 99), _c1m(99, 99, 95, 95), _c1m(95, 96, 94, 94)]
    with patch.object(pm, "_best_reversal_in_window", side_effect=lambda c, d: (
        CandleSignal("bearish_engulfing", 0.85, True) if d == "put" else None
    )):
        reason, hint = pm.analyze_postmortem(before, after, "call", "LOSS", entry_price=100.0, exit_price=94.0)
    assert reason == "direccion_equivocada"
    assert "reversión" in hint.lower()


def test_loss_with_same_direction_reversal_gives_entro_temprano():
    # Mockea: aparece patrón CALL (misma dirección) post-cierre => entró temprano.
    from candle_patterns import CandleSignal
    before = [_c1m(100, 101, 99, 100)] * 3
    after = [_c1m(100, 101, 99, 100), _c1m(100, 101, 99, 99), _c1m(99, 103, 99, 103), _c1m(103, 104, 102, 104)]
    with patch.object(pm, "_best_reversal_in_window", side_effect=lambda c, d: (
        CandleSignal("bullish_engulfing", 0.85, True) if d == "call" else None
    )):
        reason, hint = pm.analyze_postmortem(before, after, "call", "LOSS", entry_price=100.0, exit_price=104.0)
    assert reason == "entro_temprano"
    assert "entrada" in hint.lower()


def test_loss_without_reversal_gives_rango_sin_reversion():
    before = [_c1m(100, 101, 99, 100)] * 3
    after = [_c1m(100, 101, 99, 100), _c1m(100, 101, 99, 100), _c1m(100, 101, 99, 100)]
    reason, hint = pm.analyze_postmortem(before, after, "call", "LOSS", entry_price=100.0, exit_price=100.0)
    assert reason == "rango_sin_reversion"
    assert "ruido" in hint.lower() or "rango" in hint.lower()


def test_win_returns_empty_reason():
    reason, hint = pm.analyze_postmortem([], [], "call", "WIN")
    assert reason == ""
    assert hint == "ok"


def test_recorder_resolve_pending_candidate():
    tmp = tempfile.mkdtemp()
    bbr.DB_DIR = type("P", (), {"__truediv__": lambda s, x: Path(tmp)})()
    bbr.BLACK_BOX_DB = Path(tmp) / "bb_test.db"
    rec = bbr.BlackBoxRecorder()
    sid = rec.record_scan_start("STRAT-F", 1)
    cid = rec.record_candidate(sid, "STRAT-F", {
        "asset": "USDCOP_otc", "direction": "call", "score": 60.0, "payout": 87,
        "decision": "ACCEPTED", "decision_reason": "ok", "reject_reason": "",
        "candles_1m": [_c1m(100, 101, 99, 100)],
        "stoch_m15": {"k": 20, "d": 22, "estado": "SOBREVENTA"},
    })
    # Recuperar ANTES
    before = rec.get_pending_candidate_before("USDCOP_otc")
    assert before is not None
    assert before["id"] == cid
    assert before["candles_1m"]
    # Cerrar con post-mortem
    resolved = rec.resolve_candidate_for_asset(
        "USDCOP_otc", "LOSS", -10.0,
        candles_post=[_c1m(100, 101, 99, 98)],
        loss_reason="direccion_equivocada",
        improvement_hint="revisar filtro M15",
    )
    assert resolved == cid
    import sqlite3
    con = sqlite3.connect(rec.db_path)
    row = con.execute(
        "SELECT order_result, profit, loss_reason, improvement_hint, candles_post FROM scan_candidates WHERE id=?",
        (cid,),
    ).fetchone()
    con.close()
    assert row[0] == "LOSS"
    assert row[1] == -10.0
    assert row[2] == "direccion_equivocada"
    assert row[3] == "revisar filtro M15"
    assert row[4] is not None
    # Idempotencia: segundo resolve no encuentra pendiente
    second = rec.resolve_candidate_for_asset("USDCOP_otc", "LOSS", -10.0)
    assert second is None


def test_recorder_resolve_by_id_exact():
    tmp = tempfile.mkdtemp()
    bbr.DB_DIR = type("P", (), {"__truediv__": lambda s, x: Path(tmp)})()
    bbr.BLACK_BOX_DB = Path(tmp) / "bb_test2.db"
    rec = bbr.BlackBoxRecorder()
    sid = rec.record_scan_start("STRAT-F", 1)
    cid = rec.record_candidate(sid, "STRAT-F", {
        "asset": "EURUSD_otc", "direction": "call", "score": 70.0, "payout": 88,
        "decision": "ACCEPTED", "decision_reason": "ok", "reject_reason": "",
        "candles_1m": [_c1m(100, 101, 99, 100)],
        "stoch_m15": {"k": 22, "d": 24, "estado": "SOBREVENTA"},
    })
    # Recuperar por id exacto (resolución preferida de Fase 4)
    before = rec.get_candidate_by_id(cid)
    assert before is not None
    assert before["id"] == cid
    # Cerrar por id
    resolved = rec.resolve_candidate_by_id(
        cid, "WIN", 8.0,
        entry_price=100.0, exit_price=101.0,
        candles_post=[_c1m(100, 101, 99, 101)],
        loss_reason=None, improvement_hint="ok",
    )
    assert resolved == cid
    import sqlite3
    con = sqlite3.connect(rec.db_path)
    row = con.execute(
        "SELECT order_result, profit, entry_price, exit_price FROM scan_candidates WHERE id=?",
        (cid,),
    ).fetchone()
    con.close()
    assert row[0] == "WIN"
    assert row[1] == 8.0
    assert row[2] == 100.0
    assert row[3] == 101.0
