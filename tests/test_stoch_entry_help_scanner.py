"""Scanner integration tests for stoch_entry_help V3 (agotamiento verdadero).

V3: en zonas extremas (Z1 CALL / Z5 PUT) el bot ya NO entra solo por
estar en el extremo. Exige AGOTAMIENTO CONFIRMADO (cruce %K/%D en la
direccion del rebote hace >=1 vela M15 + vela de rechazo en la franja
S/R). Sin eso -> PASS (EXHAUST_WAIT), no BOOST. Con eso -> BOOST 12.

Las pruebas de VETO por contra-direccion (CALL Z5 / PUT Z1 en hard) se
mantienen igual que V2.
"""
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
        candles_5m=candles_5m,
        candles_1m=candles_1m,
        candles_15m=candles_15m,
        scan_number=1,
        blocks_by_symbol={},
        ob_tf_labels={},
        candles_h1={},
        strat_f_only_mode=False,
        maturing_snapshot={},
        initial_amount=10.0,
        _eval_override=None,
        session_id="test-session",
        bb_scan_id=1,
        sym=assets[0][0],
        payout=assets[0][1],
        flags={
            "STRAT_F_ENABLED": True,
            "STRAT_A_ONLY": False,
            "MIN_PAYOUT": 80,
            "STOCH_HELP_MODE": "hard",
            "MATURING_WATCHLIST_MODE": "live",
        },
    )


def _fake_eval(direction: str, level: float = 100.0):
    zone = ConsolidationZone(
        asset="TEST",
        ceiling=level + 1.0,
        floor=level - 1.0,
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
        math_quality=0.5,
    )


def _stoch(k: float, *, k_vals=None, d_vals=None, cruce=None, cross_ago=None) -> dict:
    return {
        "k": k,
        "d": k,
        "estado": "NEUTRO",
        "cruce": cruce,
        "divergencia": None,
        "contradicts": 0,
        "k_prev": (k_vals[-2] if k_vals and len(k_vals) >= 2 else None),
        "cross_ago": cross_ago,
        "k_vals": k_vals or [],
        "d_vals": d_vals or [],
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
    stoch_full: dict | None = None,
    candles_15m_extra=None,
):
    tmp = tempfile.mkdtemp()
    rec = _setup_bb(tmp)
    self = _make_self()
    st = stoch_full or _stoch(k)
    # Permitir inyectar una vela de agotamiento al final del cache 15m
    def _compute_stoch(candles_15m, direction=None):
        if candles_15m_extra:
            candles_15m = list(candles_15m) + candles_15m_extra
        return st
    with (
        patch.object(sc, "evaluate_strat_f", return_value=_fake_eval(direction)),
        patch("stochastic_m15.compute_stoch", side_effect=_compute_stoch),
        patch.object(sc, "get_black_box", return_value=rec),
        patch.object(cfg, "STOCH_HELP_MODE", mode),
        patch.object(sc._runtime_config, "STOCH_HELP_MODE", mode),
        patch.object(sc._runtime_config, "STRAT_A_ONLY", False),
        patch.object(sc, "STRAT_F_ENABLED", True),
    ):
        result = _evaluate_serial_with_mode(_make_cycle([(asset, payout)]), mode)
    return result, rec, self


def _evaluate_serial_with_mode(cyc, mode):
    cyc.flags["STOCH_HELP_MODE"] = mode
    return sc._evaluate_strat_f_serial(cyc)


def _cands(result):
    c = getattr(result, "f_candidate", None)
    return [c] if c is not None else []


def _bb_rows(rec: bbr.BlackBoxRecorder):
    con = __import__("sqlite3").connect(rec.db_path)
    rows = con.execute(
        "SELECT asset, decision, reject_reason, stoch_m15 FROM scan_candidates ORDER BY id"
    ).fetchall()
    con.close()
    return rows


# ── VETO por contra-direccion (igual V2) ──────────────────────────────────


@pytest.mark.asyncio
async def test_hard_call_z5_vetoes_candidate():
    result, rec, _self = await _run_scan(direction="CALL", k=85.0, mode="hard")
    cands = _cands(result)
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
    cands = _cands(result)
    assert cands == []
    rows = _bb_rows(rec)
    assert rows[0][1] == "REJECTED_STOCH"
    assert rows[0][2] == "stoch_extreme_against"
    payload = json.loads(rows[0][3])
    assert payload["zone"] == "Z1"
    assert payload["action"] == "VETO"


# ── V3: extremo sin agotamiento confirmado -> PASS (no BOOST) ──────────────


@pytest.mark.asyncio
async def test_z5_put_without_exhaustion_is_wait_not_boost():
    # PUT en Z5 (k=90) SIN cruce confirmado ni vela -> PASS (EXHAUST_WAIT)
    result, rec, _ = await _run_scan(direction="PUT", k=90.0, mode="hard")
    cands = _cands(result)
    # sigue como candidata (el fractal la aprueba), pero stoch NO la boostea
    assert len(cands) == 1
    assert "stoch_help" not in (cands[0].score_breakdown or {})
    payload = json.loads(_bb_rows(rec)[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "PASS"
    assert payload["score_delta"] == 0
    assert payload["reason"].startswith("stoch_exhaust_wait")


# ── V3: agotamiento confirmado -> BOOST 12 ─────────────────────────────────


def _put_exhausted_stoch():
    k = [60.0, 95.0, 90.0, 88.0]
    d = [72.0, 85.0, 98.0, 70.0]
    return _stoch(88.0, k_vals=k, d_vals=d, cruce="bajista", cross_ago=1)


def _call_exhausted_stoch():
    k = [20.0, 18.0, 25.0, 15.0]
    d = [22.0, 22.0, 21.0, 30.0]
    return _stoch(15.0, k_vals=k, d_vals=d, cruce="alcista", cross_ago=1)


@pytest.mark.asyncio
async def test_z5_put_exhaust_confirmed_boosts_12():
    # estrella fugaz PUT en la resistencia (ceiling ~101.0)
    candle = SimpleNamespace(ts=99, open=101.0, high=104.0, low=100.8, close=101.1)
    result, rec, _ = await _run_scan(
        direction="PUT", k=88.0, mode="hard",
        stoch_full=_put_exhausted_stoch(), candles_15m_extra=[candle],
    )
    cands = _cands(result)
    assert len(cands) == 1
    assert cands[0].score_breakdown.get("stoch_help") == 12.0
    payload = json.loads(_bb_rows(rec)[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "BOOST"
    assert payload["score_delta"] == 12
    assert payload["reason"] == "stoch_exhaust_confirmed"


@pytest.mark.asyncio
async def test_z1_call_exhaust_confirmed_boosts_12():
    candle = SimpleNamespace(ts=99, open=99.0, high=99.1, low=96.0, close=99.1)
    result, rec, _ = await _run_scan(
        direction="CALL", k=15.0, mode="hard",
        stoch_full=_call_exhausted_stoch(), candles_15m_extra=[candle],
    )
    cands = _cands(result)
    assert len(cands) == 1
    assert cands[0].score_breakdown.get("stoch_help") == 12.0
    payload = json.loads(_bb_rows(rec)[0][3])
    assert payload["zone"] == "Z1"
    assert payload["action"] == "BOOST"
    assert payload["score_delta"] == 12


# ── mode off ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mode_off_extreme_still_accepts():
    result, rec, _self = await _run_scan(direction="CALL", k=85.0, mode="off")
    cands = _cands(result)
    assert len(cands) == 1
    rows = _bb_rows(rec)
    assert rows[0][1] == "ACCEPTED"
    payload = json.loads(rows[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "PASS"
    assert payload["score_delta"] == 0


@pytest.mark.asyncio
async def test_black_box_stoch_payload_has_help_fields_on_accept():
    # PUT Z5 sin agotamiento -> aceptado por fractal, stoch PASS (espera)
    result, rec, _self = await _run_scan(direction="PUT", k=90.0, mode="hard")
    cands = _cands(result)
    assert len(cands) == 1
    payload = json.loads(_bb_rows(rec)[0][3])
    assert payload["zone"] == "Z5"
    assert payload["action"] == "PASS"  # V3: sin agotamiento -> espera, no BOOST
    assert payload["score_delta"] == 0
    assert "k" in payload
