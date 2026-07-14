"""Test de Fase 3 — cableado STRAT-F -> caja negra en scanner.py.

Verifica que, en el bloque STRAT-F de _scan_phase_evaluate_assets, se calcula
el estocástico M15 y se graba cada decisión (ACCEPTED y REJECTED) en la caja
negra con los campos correctos. Usa mocks para no tocar red ni el bot real.
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import scanner as sc
import black_box_recorder as bbr


def _make_cycle(assets):
    candles_15m = [
        SimpleNamespace(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i)
        for i in range(20)
    ]
    candles_5m = [SimpleNamespace(ts=i, open=100, high=101, low=99, close=100) for i in range(5)]
    candles_1m = [SimpleNamespace(ts=i, open=100, high=101, low=99, close=100) for i in range(5)]
    return SimpleNamespace(
        assets=assets,
        candles_5m={a[0]: candles_5m for a in assets},
        candles_1m={a[0]: candles_1m for a in assets},
        candles_15m={a[0]: candles_15m for a in assets},
        scan_number=1,
    )


def _fake_eval(direction, decision):
    return SimpleNamespace(
        direction=direction,
        strength=0.7,
        m15_context="RANGE",
        m5_event="rejection",
        skip_reason="" if decision == "ACCEPTED" else "no_pattern",
        has_signal=decision == "ACCEPTED",
        zone=(object() if decision == "ACCEPTED" else None),
        pattern_name="bullish_rejection",
    )


def _make_self():
    self = MagicMock()
    self.bot.trades = {}
    self.bot.greylist_assets = set()
    self.bot.asset_blacklist_until = {}
    self.bot.stats = {}
    self.executor._is_asset_blacklisted.return_value = False
    self.executor._compute_initial_amount.return_value = (10.0, None)
    return self


@pytest.mark.asyncio
async def test_scan_records_accepted_and_rejected_in_black_box():
    # Recorder con DB temporal (no toca la DB del día)
    tmp = tempfile.mkdtemp()
    bbr.DB_DIR = type("P", (), {"__truediv__": lambda s, x: Path(tmp)})()
    bbr.BLACK_BOX_DB = Path(tmp) / "bb_test.db"
    bbr.BLACK_BOX_LOG = Path(tmp) / "bb_test.jsonl"

    stoch_value = {"k": 20, "d": 22, "estado": "SOBREVENTA", "cruce": None, "divergencia": None, "contradicts": 0}

    with patch.object(sc, "evaluate_strat_f", side_effect=lambda *a, **k: _fake_eval("put", "ACCEPTED")), \
         patch.object(sc, "compute_stoch", return_value=stoch_value) as mock_stoch, \
         patch.object(bbr, "get_black_box") as mock_bb:
        rec = bbr.BlackBoxRecorder()
        mock_bb.return_value = rec

        self = _make_self()
        # Primer ciclo: 1 activo ACCEPTED
        with patch.object(sc, "CandidateEntry"), \
             patch.object(sc, "score_candidate"), \
             patch.object(sc, "SignalMode"):
            await sc.AssetScanner._scan_phase_evaluate_assets(self, _make_cycle([("USDCOP_otc", 87)]))

        # Segundo ciclo: 1 activo REJECTED
        with patch.object(sc, "evaluate_strat_f", side_effect=lambda *a, **k: _fake_eval("call", "REJECTED")):
            await sc.AssetScanner._scan_phase_evaluate_assets(self, _make_cycle([("EURUSD_otc", 84)]))

    # compute_stoch debe haberse llamado
    assert mock_stoch.called

    # Filas en la caja negra
    con = __import__("sqlite3").connect(bbr.BLACK_BOX_DB)
    rows = con.execute(
        "SELECT asset, decision, stoch_m15, session_id FROM scan_candidates ORDER BY id"
    ).fetchall()
    con.close()

    decisions = {r[0]: r[1] for r in rows}
    assert decisions.get("USDCOP_otc") == "ACCEPTED"
    assert decisions.get("EURUSD_otc") == "REJECTED_STRAT_F"
    stoch_rows = [r[2] for r in rows if r[2]]
    assert stoch_rows and "SOBREVENTA" in stoch_rows[0]
    assert all(r[3] for r in rows)
