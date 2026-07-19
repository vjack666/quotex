"""Hub-saved duration must reach orders via live config, not frozen imports."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config as cfg
from entry_sync import EntrySynchronizer
from executor import TradeExecutor, _live_duration_sec
from models import ConsolidationZone


@pytest.fixture(autouse=True)
def _restore_duration():
    old = cfg.DURATION_SEC
    yield
    cfg.DURATION_SEC = old


def test_live_duration_sec_reads_module_value():
    cfg.DURATION_SEC = 900
    assert _live_duration_sec() == 900
    cfg.DURATION_SEC = 300
    assert _live_duration_sec() == 300


def test_entry_synchronizer_uses_updated_duration_sec():
    sync = EntrySynchronizer(sync_enabled=False, duration_sec=300)
    assert sync.duration_sec == 300
    sync.duration_sec = 900
    timing = sync.compute_timing(candle_open_ts=0, now=1.0)
    assert timing.duration_sec == 900


@pytest.mark.asyncio
async def test_sync_to_next_candle_open_applies_live_duration():
    cfg.DURATION_SEC = 900
    bot = MagicMock()
    bot.trades = {}
    bot.dry_run = True
    bot.account_type = "PRACTICE"
    bot.failed_assets = {}
    bot._trade_tasks = set()
    bot._followup_capture_tasks = set()
    bot.stats = {}
    bot.massaniello = None
    bot.compensation_pending = False
    bot.last_entry_asset = None
    bot.last_entry_asset_streak = 0
    bot._htf_task = None
    bot.htf_scanner = None
    bot._hub_scanner = None

    ex = TradeExecutor(MagicMock(), bot)
    # Constructed with import-time default (often 300); must refresh from config.
    ex.entry_sync.duration_sec = 300
    ex.entry_sync.sync_enabled = False

    timing = await ex._sync_to_next_candle_open()

    assert ex.entry_sync.duration_sec == 900
    assert timing.duration_sec == 900


@pytest.mark.asyncio
async def test_enter_trade_default_duration_uses_live_config(monkeypatch):
    cfg.DURATION_SEC = 900
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

    ex = TradeExecutor(MagicMock(), bot)
    place = AsyncMock(return_value=(True, "DRY-900", 0.0, 0, ""))
    monkeypatch.setattr("executor.place_order", place)
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())

    zone = ConsolidationZone(
        asset="EURUSD_otc",
        ceiling=1.1,
        floor=1.0,
        bars_inside=15,
        detected_at=0.0,
        range_pct=0.001,
    )
    # breakout stage skips candle sync → uses duration_sec param / live default
    ok = await ex.enter_trade(
        "EURUSD_otc", "call", 1.0, zone, "live-duration", "breakout",
    )
    assert ok is True
    assert place.await_args.args[4] == 900
    trade = next(t for t in bot.trades.values() if t.asset == "EURUSD_otc")
    assert trade.duration_sec == 900
    assert "EURUSD_otc#900" in bot.trades
