"""Tests para el diario/calibracion STRAT-F en trade_journal.py.

Cubre: grabacion de STRAT-F (aceptada y rechazada) con strategy_origin,
tolerancia a zone=None, y reporte filtrado por STRAT-F.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trade_journal import Journal  # noqa: E402
from models import CandidateEntry, SignalMode  # noqa: E402


def _tmp_journal() -> Journal:
    fd, path = tempfile.mkstemp(suffix=".db")
    import os
    os.close(fd)
    os.unlink(path)
    j = Journal(db_path=Path(path))
    j._tmp_path = Path(path)
    return j


def _strat_f_entry(asset="TEST_otc", decision="ACCEPTED", skip=""):
    e = CandidateEntry(
        asset=asset,
        payout=92,
        zone=None,  # STRAT-F puede no tener zona en rechazos
        direction="call",
        candles=[],
        score=70.0,
        mode=SignalMode.REBOUND,
        score_breakdown={"fractal": 24.5, "context": 17.5, "payout": 18.0},
    )
    setattr(e, "_strategy_origin", "STRAT-F")
    setattr(e, "_reversal_pattern", "fractal_wyckoff")
    setattr(e, "_reversal_strength", 0.70)
    setattr(e, "_stage", "initial")
    return e, decision, skip


def test_log_candidate_strat_f_accepted(tmp_path):
    j = _tmp_journal()
    e, dec, _ = _strat_f_entry(decision="ACCEPTED")
    cid = j.log_candidate(e, decision=dec, strategy={"m15_context": "range", "strength": 70.0})
    assert cid > 0
    row = j.conn.execute(
        "SELECT strategy_origin, decision, reject_reason FROM candidates WHERE id=?",
        (cid,),
    ).fetchone()
    assert row["strategy_origin"] == "STRAT-F"
    assert row["decision"] == "ACCEPTED"
    j.close()
    j._tmp_path.unlink()


def test_log_candidate_strat_f_rejected_with_zone_none(tmp_path):
    j = _tmp_journal()
    e, dec, skip = _strat_f_entry(decision="REJECTED_STRAT_F", skip="M1 no rechaza la banda (cierra fuera)")
    cid = j.log_candidate(e, decision=dec, reject_reason=skip,
                          strategy={"m15_context": "uptrend", "strength": 60.0})
    row = j.conn.execute(
        "SELECT strategy_origin, decision, reject_reason FROM candidates WHERE id=?",
        (cid,),
    ).fetchone()
    assert row["strategy_origin"] == "STRAT-F"
    assert row["decision"] == "REJECTED_STRAT_F"
    assert "M1 no rechaza" in row["reject_reason"]
    j.close()
    j._tmp_path.unlink()


def test_query_and_report_strat_f(tmp_path, capsys):
    j = _tmp_journal()
    e1, d1, _ = _strat_f_entry(asset="AAA_otc", decision="ACCEPTED")
    e2, d2, s2 = _strat_f_entry(asset="BBB_otc", decision="REJECTED_STRAT_F",
                                 skip="Zona muy joven")
    j.log_candidate(e1, decision=d1, strategy={"strength": 70.0})
    j.log_candidate(e2, decision=d2, reject_reason=s2, strategy={"strength": 55.0})
    rows = j.query_strat_f(days=1)
    assert len(rows) == 2
    j.print_strat_f_report(days=1)
    out = capsys.readouterr().out
    assert "STRAT-F" in out
    assert "Aceptadas" in out
    assert "Zona muy joven" in out  # aparece en motivos de rechazo
    j.close()
    j._tmp_path.unlink()
