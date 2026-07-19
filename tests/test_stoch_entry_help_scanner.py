"""Scanner integration tests for stoch_entry_help (mocked STRAT-F + stoch)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import black_box_recorder as bbr
import config as cfg
import scanner as sc
from models import ConsolidationZone


def _make_cycle(assets):
    candles_15m = [
        SimpleNamespace(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i)
        for i in range(20)
    ]
    candles_5m = [SimpleNamespace(ts=i, open=100, high=101, low=99, close=100) for i in range(5)]
    candles_1m = [
        SimpleNamespace(ts=i, open=100, high=101, low=99, close=100) for i in range(5)
    ]
    return SimpleNamespace(
        assets=assets,
        candles_5m={a[0]: candles_5m for a in assets},
        candles_1m={a[0]: candles_1m for a in assets},
        candles_15m={a[0]: candles_15m for a in assets},
        scan_number=1,
        blocks_by_symbol={},
        ob_tf_labels={},
        candles_h1={},
    )


def _fake_eval(direction: str):
    zone = ConsolidationZone(
        asset="TEST",
        ceiling=101.0,
        floor=99.0,
        bars_inside=10,
        detected_at=0.0,
        range_pct=0.002,
    )
    return SimpleNamespace(
        direction=direction,
        strength=0.8,
        m15_context="RANGE",
        m5_event="rejection",
        skip_reason="",
        has_signal=True,
        zone=zone,
        pattern_name="bullish_rejection",
    )


def _stoch(k: float) -> dict:
    return {
        "k": k,
        "d": k,
        "estado": "NEUTRO",
        "cruce": None,
        "divergencia": None,
        "contradicts": 0,
    }


def _make_self():
    self = MagicMock()
    self.bot.trades = {}
    self.bot.greylist_assets = set()
    self.bot.asset_blacklist_until = {}
    self.bot.failed_assets = {}
    self.bot.stats = {}
    self.bot.zones = {}
    self.bot.last_known_price = {}
    self.bot.order_blocks_by_asset = {}
    self.executor._is_asset_blacklisted.return_value = False
    self.executor._compute_initial_amount.return_value = (10.0, None)
    return self


def _setup_bb(tmp: str) -> bbr.BlackBoxRecorder:
    """Fresh recorder on a temp DB; reset singleton so paths do not stick."""
    bbr._recorder = None
    bbr.BLACK_BOX_DB = Path(tmp) / "bb_stoch_help.db"
    bbr.BLACK_BOX_LOG = Path(tmp) / "bb_stoch_help.jsonl"
    return bbr.BlackBoxRecorder()


async def _run_scan(
    *,
    direction: str,
    k: float,
    mode: str,
    asset: str = "EURUSD_otc",
    payout: int = 87,
):
    tmp = tempfile.mkdtemp()
    rec = _setup_bb(tmp)
    self = _make_self()
    # Patch sc.get_black_box (scanner binds the name at import time).
    with (
        patch.object(sc, "evaluate_strat_f", return_value=_fake_eval(direction)),
        patch.object(sc, "compute_stoch", return_value=_stoch(k)),
        patch.object(sc, "get_black_box", return_value=rec),
        patch.object(cfg, "STOCH_HELP_MODE", mode),
        patch.object(sc._runtime_config, "STOCH_HELP_MODE", mode),
        patch.object(sc._runtime_config, "STRAT_A_ONLY", False),
        patch.object(sc, "STRAT_F_ENABLED", True),
    ):
        result = await sc.AssetScanner._scan_phase_evaluate_assets(
            self, _make_cycle([(asset, payout)])
        )
    return result, rec, self


def _bb_rows(rec: bbr.BlackBoxRecorder):
    con = __import__("sqlite3").connect(rec.db_path)
    rows = con.execute(
        "SELECT asset, decision, reject_reason, stoch_m15 FROM scan_candidates ORDER BY id"
    ).fetchall()
    con.close()
    return rows


@pytest.mark.asyncio
async def test_hard_call_z5_vetoes_candidate():
    result, rec, _self = await _run_scan(direction="CALL", k=85.0, mode="hard")
    cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert cands == []
    rows = _bb_rows(rec)
    assert rows, "expected black-box row"
    asset, decision, reject_reason, stoch_raw = rows[0]
    assert decision == "REJECTED_STOCH"
    assert reject_reason == "stoch_extreme_against"
    payload = json.loads(stoch_raw)
    assert payload["zone"] == "Z5"
    assert payload["action"] == "VETO"
    assert payload["score_delta"] == 0


@pytest.mark.asyncio
async def test_hard_put_z1_vetoes_candidate():
    result, rec, _self = await _run_scan(direction="PUT", k=10.0, mode="hard")
    cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert cands == []
    rows = _bb_rows(rec)
    assert rows[0][1] == "REJECTED_STOCH"
    assert rows[0][2] == "stoch_extreme_against"
    payload = json.loads(rows[0][3])
    assert payload["zone"] == "Z1"
    assert payload["action"] == "VETO"


@pytest.mark.asyncio
async def test_soft_call_z5_no_veto():
    result, rec, _self = await _run_scan(direction="CALL", k=85.0, mode="soft")
    cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert len(cands) == 1
    assert "stoch_help" not in (cands[0].score_breakdown or {})
    rows = _bb_rows(rec)
    assert rows[0][1] == "ACCEPTED"
    payload = json.loads(rows[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "PASS"
    assert payload["score_delta"] == 0


@pytest.mark.asyncio
async def test_hard_call_z1_boosts_score_by_10():
    # Baseline: mode off (no boost)
    base_result, _base_rec, _ = await _run_scan(direction="CALL", k=10.0, mode="off")
    base_cands = [
        c for c in base_result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"
    ]
    assert len(base_cands) == 1
    base_score = base_cands[0].score

    # Boosted: hard + Z1 CALL → +10
    boost_result, rec, _ = await _run_scan(direction="CALL", k=10.0, mode="hard")
    boost_cands = [
        c for c in boost_result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"
    ]
    assert len(boost_cands) == 1
    assert boost_cands[0].score == pytest.approx(base_score + 10.0)
    assert boost_cands[0].score_breakdown.get("stoch_help") == 10.0
    payload = json.loads(_bb_rows(rec)[0][3])
    assert payload["zone"] == "Z1"
    assert payload["action"] == "BOOST"
    assert payload["score_delta"] == 10


@pytest.mark.asyncio
async def test_mode_off_extreme_still_accepts():
    result, rec, _self = await _run_scan(direction="CALL", k=85.0, mode="off")
    cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert len(cands) == 1
    rows = _bb_rows(rec)
    assert rows[0][1] == "ACCEPTED"
    payload = json.loads(rows[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "PASS"
    assert payload["score_delta"] == 0


@pytest.mark.asyncio
async def test_black_box_stoch_payload_has_help_fields_on_accept():
    result, rec, _self = await _run_scan(direction="PUT", k=90.0, mode="hard")
    cands = [c for c in result["candidates"] if getattr(c, "_strategy_origin", "") == "STRAT-F"]
    assert len(cands) == 1
    payload = json.loads(_bb_rows(rec)[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "BOOST"
    assert payload["score_delta"] == 10
    assert "k" in payload
