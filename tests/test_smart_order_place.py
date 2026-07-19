"""Tests for smart_order_place: prewarm, skip_open_wait, last_order_attempt, hub enrich."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
ROOT = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config as cfg
from executor import TradeExecutor
from models import ConsolidationZone, EntryTimingInfo


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
    bot.last_order_attempt = None
    bot._trade_tasks = set()
    bot._followup_capture_tasks = set()
    bot.stats = {
        "martin_attempts_session": 0,
        "entries": 0,
        "strat_a_signals": 0,
        "rejected_same_asset_limit": 0,
        "martins": 0,
    }
    bot.massaniello = MagicMock()
    bot.massaniello.is_session_complete.return_value = False
    bot.massaniello.is_session_failed.return_value = False
    bot.massaniello.is_session_timeout.return_value = False
    bot.massaniello.is_session_exhausted.return_value = False
    bot.massaniello.can_enter.return_value = True
    bot.massaniello.session_start_time = None
    bot.compensation_pending = False
    bot.last_entry_asset = None
    bot.last_entry_asset_streak = 0
    bot._htf_task = None
    bot.htf_scanner = None
    bot._hub_scanner = None
    bot.session_start_time = None
    bot.continuous = None
    return bot


def test_order_fail_quarantine_cycles_default():
    assert cfg.ORDER_FAIL_QUARANTINE_CYCLES == 5


@pytest.mark.asyncio
async def test_skip_open_wait_skips_full_sync_when_lag_ok(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    ok_timing = EntryTimingInfo(
        ok=True,
        lag_sec=0.1,
        duration_sec=300,
        time_since_open_sec=0.1,
        secs_to_close_sec=59.9,
        decision="SYNCED_ENTRY_OPEN",
    )
    sync_mock = AsyncMock(return_value=ok_timing)
    monkeypatch.setattr(ex, "_sync_to_next_candle_open", sync_mock)
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    monkeypatch.setattr(
        "executor.place_order",
        AsyncMock(return_value=(True, "OID-1", 1.05, 1, "")),
    )
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    monkeypatch.setattr(
        ex.entry_sync,
        "compute_timing",
        MagicMock(return_value=ok_timing),
    )

    ok = await ex.enter_trade(
        "EURUSD_otc", "call", 1.0, _zone(), "alt-retry", "initial",
        skip_open_wait=True,
    )
    assert ok is True
    sync_mock.assert_not_awaited()
    assert bot.last_order_attempt is not None
    assert bot.last_order_attempt["status"] == "accepted"
    assert bot.last_order_attempt["asset"] == "EURUSD_otc"


@pytest.mark.asyncio
async def test_skip_open_wait_falls_back_to_full_sync_when_lag_bad(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    bad_timing = EntryTimingInfo(
        ok=False,
        lag_sec=12.0,
        duration_sec=300,
        time_since_open_sec=12.0,
        secs_to_close_sec=48.0,
        decision="REJECT_LATE_ENTRY",
    )
    good_timing = EntryTimingInfo(
        ok=True,
        lag_sec=0.05,
        duration_sec=300,
        time_since_open_sec=0.05,
        secs_to_close_sec=59.95,
        decision="SYNCED_ENTRY_OPEN",
    )
    sync_mock = AsyncMock(return_value=good_timing)
    monkeypatch.setattr(ex, "_sync_to_next_candle_open", sync_mock)
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    monkeypatch.setattr(
        "executor.place_order",
        AsyncMock(return_value=(True, "OID-2", 1.05, 1, "")),
    )
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    monkeypatch.setattr(
        ex.entry_sync,
        "compute_timing",
        MagicMock(return_value=bad_timing),
    )

    ok = await ex.enter_trade(
        "GBPUSD_otc", "put", 1.0, _zone("GBPUSD_otc"), "alt-late", "initial",
        skip_open_wait=True,
    )
    assert ok is True
    sync_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_prewarm_starts_before_open_wait(monkeypatch):
    """Prewarm task is scheduled before open-wait; buy only after prewarm completes."""
    import asyncio

    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    events: list[str] = []
    prewarm_scheduled = False

    async def fake_prewarm(_label=""):
        events.append("prewarm_run")
        await asyncio.sleep(0.02)
        events.append("prewarm_done")

    async def fake_sync(_signal_ts=None):
        # create_task(prewarm) must already have been issued.
        assert prewarm_scheduled is True
        events.append("sync")
        await asyncio.sleep(0.05)
        return EntryTimingInfo(
            ok=True,
            lag_sec=0.0,
            duration_sec=60,
            time_since_open_sec=0.0,
            secs_to_close_sec=60.0,
            decision="SYNCED_ENTRY_OPEN",
        )

    real_create_task = asyncio.create_task

    def tracking_create_task(coro, **kwargs):
        nonlocal prewarm_scheduled
        # First create_task in enter_trade path is prewarm of trade_client.
        if not prewarm_scheduled:
            prewarm_scheduled = True
            events.append("prewarm_scheduled")
        return real_create_task(coro, **kwargs)

    place = AsyncMock(return_value=(True, "OID-P", 1.0, 1, ""))

    def place_side_effect(*_a, **_k):
        events.append("place")
        assert "prewarm_done" in events
        return place.return_value

    place.side_effect = place_side_effect

    monkeypatch.setattr(ex, "_reconnect_if_needed", fake_prewarm)
    monkeypatch.setattr(ex, "_sync_to_next_candle_open", fake_sync)
    monkeypatch.setattr("executor.place_order", place)
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    monkeypatch.setattr(asyncio, "create_task", tracking_create_task)

    ok = await ex.enter_trade(
        "EURUSD_otc", "call", 1.0, _zone(), "prewarm", "initial",
    )
    assert ok is True
    assert prewarm_scheduled is True
    assert "prewarm_done" in events
    assert "sync" in events
    assert "place" in events
    assert events.index("prewarm_scheduled") < events.index("sync")
    assert events.index("prewarm_done") < events.index("place")


@pytest.mark.asyncio
async def test_last_order_attempt_set_on_fail(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    monkeypatch.setattr(
        ex,
        "_sync_to_next_candle_open",
        AsyncMock(
            return_value=EntryTimingInfo(
                ok=True,
                lag_sec=0.0,
                duration_sec=60,
                time_since_open_sec=0.0,
                secs_to_close_sec=60.0,
                decision="SYNC_DISABLED",
            )
        ),
    )
    monkeypatch.setattr(
        "executor.place_order",
        AsyncMock(return_value=(False, "", 0.0, 0, "buy_timeout_60s")),
    )

    ok = await ex.enter_trade(
        "XAUUSD_otc", "call", 1.0, _zone("XAUUSD_otc"), "fail", "initial",
    )
    assert ok is False
    attempt = bot.last_order_attempt
    assert attempt["status"] == "failed"
    assert attempt["reason"] == "buy_timeout_60s"
    assert attempt["asset"] == "XAUUSD_otc"
    assert attempt["direction"] == "call"
    assert isinstance(attempt["ts"], float)
    assert bot.failed_assets["XAUUSD_otc"] == cfg.ORDER_FAIL_QUARANTINE_CYCLES


@pytest.mark.asyncio
async def test_last_order_attempt_set_on_success(monkeypatch):
    bot = _bot()
    client = MagicMock()
    client.get_balance = AsyncMock(return_value=1000.0)
    ex = TradeExecutor(client, bot)
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    monkeypatch.setattr(
        ex,
        "_sync_to_next_candle_open",
        AsyncMock(
            return_value=EntryTimingInfo(
                ok=True,
                lag_sec=0.0,
                duration_sec=60,
                time_since_open_sec=0.0,
                secs_to_close_sec=60.0,
                decision="SYNC_DISABLED",
            )
        ),
    )
    monkeypatch.setattr(
        "executor.place_order",
        AsyncMock(return_value=(True, "OK-1", 1.1, 7, "")),
    )
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())

    ok = await ex.enter_trade(
        "EURUSD_otc", "put", 2.0, _zone(), "ok", "initial",
    )
    assert ok is True
    assert bot.last_order_attempt["status"] == "accepted"
    assert bot.last_order_attempt["direction"] == "put"


@pytest.mark.asyncio
async def test_unexpected_fail_quarantine_cycles(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    monkeypatch.setattr(
        "executor.place_order",
        AsyncMock(return_value=(False, "", 0.0, 0, "unexpected")),
    )
    # breakout skips open sync
    ok = await ex.enter_trade(
        "USDJPY_otc", "call", 1.0, _zone("USDJPY_otc"), "u", "breakout",
    )
    assert ok is False
    assert bot.failed_assets["USDJPY_otc"] == 5
    assert bot.last_order_attempt["reason"] == "unexpected"


def test_hub_enrich_includes_last_order_attempt():
    import hub.server as hub_server

    base: dict = {}
    bot = MagicMock()
    bot.current_balance = 100.0
    bot.stats = {"scans": 3, "strat_a_wins": 1, "strat_a_losses": 0}
    bot.trades = {}
    bot.massaniello = None
    bot.last_order_attempt = {
        "asset": "XAUUSD_otc",
        "direction": "call",
        "status": "failed",
        "reason": "buy_timeout_60s",
        "ts": 1720000000.0,
    }
    prev = hub_server._bot_ref
    try:
        hub_server._bot_ref = bot
        hub_server._enrich_with_bot(base)
    finally:
        hub_server._bot_ref = prev

    assert "last_order_attempt" in base
    assert base["last_order_attempt"]["reason"] == "buy_timeout_60s"
    assert base["last_order_attempt"]["status"] == "failed"


def test_hub_ui_contains_order_attempt_line():
    html = (ROOT / "hub" / "static" / "index.html").read_text(encoding="utf-8")
    assert "t-order-attempt" in html
    assert "last_order_attempt" in html
    assert "esperando open" in html


def test_is_hard_order_fail_classifies_reasons():
    assert TradeExecutor._is_hard_order_fail("buy_timeout_60s")
    assert TradeExecutor._is_hard_order_fail("unexpected")
    assert TradeExecutor._is_hard_order_fail("connection lost")
    assert not TradeExecutor._is_hard_order_fail("insufficient_funds")
