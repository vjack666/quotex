"""Multi-duration data collection: 1 signal → N expiries; Massaniello primary only."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config as cfg
from black_box_recorder import BlackBoxRecorder
from executor import TradeExecutor
from models import ConsolidationZone, EntryTimingInfo, TradeState, make_trade_key


def _zone(asset: str = "EURUSD_otc") -> ConsolidationZone:
    return ConsolidationZone(
        asset=asset,
        ceiling=1.1,
        floor=1.0,
        bars_inside=15,
        detected_at=0.0,
        range_pct=0.001,
    )


def _bot() -> MagicMock:
    bot = MagicMock()
    bot.trades = {}
    bot.dry_run = True
    bot.account_type = "PRACTICE"
    bot.failed_assets = {}
    bot._trade_tasks = set()
    bot._followup_capture_tasks = set()
    bot.stats = {
        "martin_attempts_session": 0,
        "entries": 0,
        "strat_a_signals": 0,
        "rejected_same_asset_limit": 0,
        "martins": 0,
        "strat_a_wins": 0,
        "strat_a_losses": 0,
        "multi_duration_wins": 0,
        "multi_duration_losses": 0,
    }
    bot.massaniello = MagicMock()
    bot.massaniello.is_session_complete.return_value = False
    bot.massaniello.is_session_failed.return_value = False
    bot.massaniello.is_session_timeout.return_value = False
    bot.massaniello.is_session_exhausted.return_value = False
    bot.massaniello.can_enter.return_value = True
    bot.massaniello.session_start_time = None
    bot.massaniello.register_win = MagicMock(return_value=(1.0, "OK"))
    bot.massaniello.register_loss = MagicMock(return_value=(0.0, "OK"))
    bot.compensation_pending = False
    bot.last_entry_asset = None
    bot.last_entry_asset_streak = 0
    bot._htf_task = None
    bot.htf_scanner = None
    bot._hub_scanner = None
    bot.session_start_time = None
    bot.current_balance = 1000.0
    bot.session_start_balance = 1000.0
    bot.cycle_id = 1
    bot.cycle_ops = 0
    bot.cycle_wins = 0
    bot.cycle_losses = 0
    bot.cycle_profit = 0.0
    bot.cycle_start_balance = 1000.0
    bot.pending_martin = {}
    bot.watched_candidates = {}
    bot.asset_loss_streaks = {}
    bot.asset_blacklist_until = {}
    bot.continuous = None
    bot.session_stop_hit = False
    return bot


def _ok_timing() -> EntryTimingInfo:
    return EntryTimingInfo(
        ok=True,
        lag_sec=0.0,
        duration_sec=300,
        time_since_open_sec=0.0,
        secs_to_close_sec=300.0,
        decision="SYNC_DISABLED",
    )


def _patch_multi_entry(ex: TradeExecutor, monkeypatch, place=None):
    """Shared mocks for simultaneous multi-duration path (single timing + M1)."""
    if place is None:
        place = AsyncMock(return_value=(True, "DRY-MD", 1.05, 0, ""))
    monkeypatch.setattr("executor.place_order", place)
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    monkeypatch.setattr(ex, "_resolve_entry_timing", AsyncMock(return_value=_ok_timing()))
    monkeypatch.setattr(ex, "_m1_micro_confirm_pre_buy", AsyncMock(return_value=(True, "ok")))
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    return place


@pytest.fixture
def multi_on(monkeypatch):
    monkeypatch.setattr(cfg, "MULTI_DURATION_DATA_COLLECTION", True)
    monkeypatch.setattr(cfg, "MULTI_DURATION_SECS", (60, 300, 600, 900))
    monkeypatch.setattr(cfg, "MULTI_DURATION_MASSANIELLO_PRIMARY_SEC", 300)
    monkeypatch.setattr(cfg, "MULTI_DURATION_PARALLEL", True)
    monkeypatch.setattr(cfg, "MULTI_DURATION_IGNORE_SESSION_BLOCKS", True)
    monkeypatch.setattr(cfg, "MAX_CONCURRENT_TRADES", 4)
    yield


@pytest.fixture
def multi_off(monkeypatch):
    monkeypatch.setattr(cfg, "MULTI_DURATION_DATA_COLLECTION", False)
    yield


@pytest.mark.asyncio
async def test_enter_multi_duration_places_four_trade_keys(multi_on, monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    place = _patch_multi_entry(ex, monkeypatch)

    ok = await ex.enter_multi_duration(
        "EURUSD_otc",
        "call",
        1.0,
        _zone(),
        "multi-test",
        "initial",
        strategy_origin="STRAT-F",
        payout=85,
        score_original=80.0,
        black_box_cids=[1, 2, 3, 4],
    )
    assert ok is True
    assert place.await_count == 4
    durations_sent = sorted(c.args[4] for c in place.await_args_list)
    assert durations_sent == [60, 300, 600, 900]
    # Single open-sync + single M1 check for the batch
    assert ex._resolve_entry_timing.await_count == 1
    assert ex._m1_micro_confirm_pre_buy.await_count == 1
    for d in (60, 300, 600, 900):
        key = make_trade_key("EURUSD_otc", d)
        assert key in bot.trades
        assert bot.trades[key].asset == "EURUSD_otc"
        assert bot.trades[key].duration_sec == d
        assert bot.trades[key].trade_key == key
    # Same-asset streak registered once
    assert bot.last_entry_asset == "EURUSD_otc"
    assert bot.last_entry_asset_streak == 1


@pytest.mark.asyncio
async def test_single_duration_path_when_multi_off(multi_off, monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    place = AsyncMock(return_value=(True, "DRY-1", 1.05, 0, ""))
    monkeypatch.setattr("executor.place_order", place)
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    monkeypatch.setattr(ex, "_resolve_entry_timing", AsyncMock(return_value=_ok_timing()))
    monkeypatch.setattr(ex, "_m1_micro_confirm_pre_buy", AsyncMock(return_value=(True, "ok")))
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    ok = await ex.enter_trade(
        "EURUSD_otc",
        "put",
        1.0,
        _zone(),
        "single",
        "initial",
        duration_sec=300,
        strategy_origin="STRAT-F",
    )
    assert ok is True
    assert place.await_count == 1
    assert make_trade_key("EURUSD_otc", 300) in bot.trades


@pytest.mark.asyncio
async def test_multi_duration_parallel_faster_than_sequential(multi_on, monkeypatch):
    """Parallel gather: wall time ~ max(leg) not sum(leg)."""
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    delay = 0.05

    async def slow_place(*_a, **_k):
        await asyncio.sleep(delay)
        return (True, "DRY-P", 1.05, 0, "")

    place = AsyncMock(side_effect=slow_place)
    _patch_multi_entry(ex, monkeypatch, place=place)
    monkeypatch.setattr(cfg, "MULTI_DURATION_PARALLEL", True)

    t0 = time.perf_counter()
    ok = await ex.enter_multi_duration(
        "EURUSD_otc",
        "call",
        1.0,
        _zone(),
        "parallel-test",
        "initial",
        strategy_origin="STRAT-F",
    )
    elapsed = time.perf_counter() - t0
    assert ok is True
    assert place.await_count == 4
    # 4 * 0.05 = 0.20 sequential; parallel should be well under 0.15
    assert elapsed < delay * 3
    assert ex._resolve_entry_timing.await_count == 1


@pytest.mark.asyncio
async def test_ignore_session_blocks_still_places_legs(multi_on, monkeypatch):
    """Data mode: Massaniello can_enter=False must not block the multi batch."""
    bot = _bot()
    bot.massaniello.can_enter.return_value = False
    bot.massaniello.is_session_exhausted.return_value = True
    ex = TradeExecutor(MagicMock(), bot)
    # Force Massaniello path so _massaniello_session_blocks_entry is active.
    monkeypatch.setattr(ex, "_uses_massaniello", lambda: True)
    place = _patch_multi_entry(ex, monkeypatch)
    monkeypatch.setattr(cfg, "MULTI_DURATION_IGNORE_SESSION_BLOCKS", True)

    ok = await ex.enter_multi_duration(
        "EURUSD_otc",
        "put",
        1.0,
        _zone(),
        "ignore-block-test",
        "initial",
        strategy_origin="STRAT-F",
    )
    assert ok is True
    assert place.await_count == 4
    assert len(bot.trades) == 4


@pytest.mark.asyncio
async def test_session_blocks_when_ignore_disabled(multi_on, monkeypatch):
    bot = _bot()
    bot.massaniello.can_enter.return_value = False
    bot.massaniello.is_session_exhausted.return_value = True
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(ex, "_uses_massaniello", lambda: True)
    place = _patch_multi_entry(ex, monkeypatch)
    monkeypatch.setattr(cfg, "MULTI_DURATION_IGNORE_SESSION_BLOCKS", False)

    ok = await ex.enter_multi_duration(
        "EURUSD_otc",
        "call",
        1.0,
        _zone(),
        "block-test",
        "initial",
        strategy_origin="STRAT-F",
    )
    assert ok is False
    assert place.await_count == 0
    assert bot.trades == {}


@pytest.mark.asyncio
async def test_resolve_primary_updates_massaniello_secondary_does_not(
    multi_on, monkeypatch,
):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(ex, "refresh_balance_and_risk", AsyncMock(return_value=False))
    monkeypatch.setattr(ex, "_uses_massaniello", lambda: True)
    monkeypatch.setattr(ex, "_maybe_stop_massaniello_session", MagicMock())
    monkeypatch.setattr(ex, "_sync_massaniello_session_start", MagicMock())
    monkeypatch.setattr(ex, "_update_cycle_after_result", MagicMock())
    monkeypatch.setattr(ex, "_register_asset_outcome", MagicMock())
    j = MagicMock()
    j._conn = None
    monkeypatch.setattr("executor.get_journal", lambda: j)
    monkeypatch.setattr("executor.get_black_box", MagicMock())

    primary = TradeState(
        asset="EURUSD_otc",
        direction="call",
        amount=1.0,
        entry_price=1.05,
        ceiling=1.1,
        floor=1.0,
        order_id="OID-P",
        duration_sec=300,
        payout=85,
        strategy_origin="STRAT-A",
        trade_key=make_trade_key("EURUSD_otc", 300),
        black_box_cid=0,
    )
    secondary = TradeState(
        asset="EURUSD_otc",
        direction="call",
        amount=1.0,
        entry_price=1.05,
        ceiling=1.1,
        floor=1.0,
        order_id="OID-S",
        duration_sec=60,
        payout=85,
        strategy_origin="STRAT-A",
        trade_key=make_trade_key("EURUSD_otc", 60),
        black_box_cid=0,
    )
    bot.trades[primary.trade_key] = primary
    bot.trades[secondary.trade_key] = secondary
    bot.dry_run = False

    # Force WIN interpretation without broker
    monkeypatch.setattr(
        ex,
        "_interpret_broker_result",
        MagicMock(return_value=("WIN", 0.85)),
    )
    ex.client = MagicMock()
    ex.client.check_win = AsyncMock(return_value=True)
    primary.order_ref = 11
    secondary.order_ref = 12

    await ex._resolve_trade(primary, primary.trade_key)
    assert bot.massaniello.register_win.call_count == 1
    assert primary.trade_key not in bot.trades

    await ex._resolve_trade(secondary, secondary.trade_key)
    # Still only one Massaniello registration
    assert bot.massaniello.register_win.call_count == 1
    assert bot.stats["multi_duration_wins"] == 1
    assert secondary.trade_key not in bot.trades


def test_make_trade_key_format():
    assert make_trade_key("EURUSD_otc", 60) == "EURUSD_otc#60"
    assert make_trade_key("EURUSD_otc", 900) == "EURUSD_otc#900"


def test_black_box_duration_sec_column(tmp_path, multi_on):
    db = tmp_path / "bb_multi.db"
    log = tmp_path / "bb_multi.jsonl"
    rec = BlackBoxRecorder.__new__(BlackBoxRecorder)
    rec.db_path = str(db)
    rec.log_path = str(log)
    rec._init_db()

    scan_id = rec.record_scan_start("STRAT-F", 1, {"market_state": "ranging"})
    cid = rec.record_candidate(
        scan_id,
        "STRAT-F",
        {
            "asset": "EURUSD_otc",
            "direction": "call",
            "score": 80.0,
            "payout": 85,
            "decision": "ACCEPTED",
            "duration_sec": 300,
            "strategy_details": {"event": "fractal"},
        },
    )
    assert cid > 0
    import sqlite3

    con = sqlite3.connect(str(db))
    row = con.execute(
        "SELECT duration_sec, order_result FROM scan_candidates WHERE id=?",
        (cid,),
    ).fetchone()
    con.close()
    assert row[0] == 300
    assert row[1] is None

    # Clone for 60s leg
    cid2 = rec.clone_candidate_for_duration(cid, 60)
    assert cid2 > 0 and cid2 != cid
    con = sqlite3.connect(str(db))
    row2 = con.execute(
        "SELECT duration_sec FROM scan_candidates WHERE id=?", (cid2,)
    ).fetchone()
    con.close()
    assert row2[0] == 60

    # WIN resolve writes order_result
    rec.resolve_candidate_by_id(cid, "WIN", 0.85, entry_price=1.05)
    con = sqlite3.connect(str(db))
    row3 = con.execute(
        "SELECT order_result, profit FROM scan_candidates WHERE id=?", (cid,)
    ).fetchone()
    con.close()
    assert row3[0] == "WIN"
    assert row3[1] == 0.85


def test_is_massaniello_primary_trade(multi_on):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    t_primary = TradeState(
        asset="X", direction="call", amount=1, entry_price=1,
        ceiling=1, floor=0, duration_sec=300,
    )
    t_other = TradeState(
        asset="X", direction="call", amount=1, entry_price=1,
        ceiling=1, floor=0, duration_sec=60,
    )
    assert ex._is_massaniello_primary_trade(t_primary) is True
    assert ex._is_massaniello_primary_trade(t_other) is False


def test_is_massaniello_primary_when_multi_off(multi_off):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    t = TradeState(
        asset="X", direction="call", amount=1, entry_price=1,
        ceiling=1, floor=0, duration_sec=60,
    )
    assert ex._is_massaniello_primary_trade(t) is True
