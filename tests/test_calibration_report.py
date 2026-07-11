"""Tests para calibration_report.py (reporte de calibracion STRAT-F)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import os  # noqa: E402

from trade_journal import Journal  # noqa: E402
from models import CandidateEntry, SignalMode  # noqa: E402
from calibration_report import classify_skip, build_calibration  # noqa: E402


def _tmp_journal():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    j = Journal(db_path=Path(path))
    return j, Path(path)
def _feed(j: Journal, asset, decision, skip=""):
    e = CandidateEntry(
        asset=asset, payout=92, zone=None, direction="call", candles=[],
        score=70.0, mode=SignalMode.REBOUND,
        score_breakdown={"fractal": 24.0, "context": 17.0, "payout": 18.0},
    )
    setattr(e, "_strategy_origin", "STRAT-F")
    setattr(e, "_reversal_pattern", "fractal_wyckoff")
    setattr(e, "_reversal_strength", 0.70)
    j.log_candidate(e, decision=decision, reject_reason=skip,
                    strategy={"strength": 70.0})


def test_classify_skip_known_reasons():
    assert classify_skip("zona muy joven (2 < 3 velas M5)") == "R3 edad zona"
    assert classify_skip("M1 no rechaza la banda (cierra fuera)") == "R4 banda M1"
    assert classify_skip("CALL contra tendencia M15") == "R1 tendencia"
    assert classify_skip("payout 75% < minimo 80%") == "R2 payout"
    assert classify_skip("score 55 < minimo 60") == "R6 score"
    assert classify_skip("M15 rango roto: no operar rebotes") == "CTX M15 roto"


def test_build_calibration_groups_and_suggests():
    j, path = _tmp_journal()
    # 1 aceptada (PENDING), 11 rechazadas R4, 2 rechazadas R3
    _feed(j, "AAA_otc", "ACCEPTED")
    for i in range(11):
        _feed(j, f"R{i}_otc", "REJECTED_STRAT_F",
              "M1 no rechaza la banda (cierra fuera)")
    for i in range(2):
        _feed(j, f"Z{i}_otc", "REJECTED_STRAT_F",
              "zona muy joven (2 < 3 velas M5)")
    c = build_calibration(days=1, journal=j)
    assert c["total"] == 14
    assert c["accepted"] == 1
    assert c["rejected"] == 13
    assert c["reasons"]["R4 banda M1"] == 11
    assert c["reasons"]["R3 edad zona"] == 2
    # Sin resueltas -> pista de no ajustar
    assert "Sin trades resueltas" in c["global_hint"]
    j.close()
    path.unlink(missing_ok=True)


def test_build_calibration_low_winrate_suggests_tighten():
    j, path = _tmp_journal()
    for _ in range(3):
        _feed(j, "WIN_otc", "ACCEPTED")
    for _ in range(7):
        _feed(j, "LOSS_otc", "ACCEPTED")  # marcamos como LOSS via outcome
    # Las aceptadas necesitan outcome WIN/LOSS; log_candidate no lo setea.
    # Forzamos update directo para simular resultado.
    j.conn.execute("UPDATE candidates SET outcome='WIN' WHERE id=1")
    j.conn.execute("UPDATE candidates SET outcome='LOSS' WHERE id IN (2,3,4,5,6,7,8,9,10)")
    j.conn.commit()
    c = build_calibration(days=1, journal=j)
    assert c["wins"] == 1
    assert c["losses"] == 9
    assert c["win_rate"] < 50.0
    assert "APRETAR" in c["global_hint"]
    j.close()
    path.unlink(missing_ok=True)
