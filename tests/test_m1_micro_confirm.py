"""Tests for M1 micro-trend confirmation gate (pure + pre-buy wiring)."""
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
from m1_micro_confirm import confirm_m1_micro
from models import Candle, ConsolidationZone, EntryTimingInfo
from executor import TradeExecutor


def _c(o: float, h: float, l: float, c: float, ts: int = 0) -> Candle:
    return Candle(ts=ts, open=o, high=h, low=l, close=c)


def _bearish_last() -> list[Candle]:
    """Last candle bearish and lower than prev close (against CALL)."""
    return [
        _c(1.10, 1.12, 1.09, 1.11, ts=1),
        _c(1.11, 1.12, 1.08, 1.09, ts=2),  # close < open, close < prev close
    ]


def _bullish_last() -> list[Candle]:
    """Last candle bullish and higher than prev close (against PUT)."""
    return [
        _c(1.10, 1.12, 1.09, 1.11, ts=1),
        _c(1.11, 1.15, 1.10, 1.14, ts=2),  # close > open, close > prev close
    ]


def _aligned_call() -> list[Candle]:
    """Last not clearly against CALL (bullish body)."""
    return [
        _c(1.10, 1.12, 1.09, 1.11, ts=1),
        _c(1.11, 1.14, 1.10, 1.13, ts=2),  # close > open
    ]


def test_call_against_returns_false():
    ok, reason, metrics = confirm_m1_micro(_bearish_last(), "call")
    assert ok is False
    assert reason == "m1_against_call"
    assert metrics["last_close"] == 1.09
    assert metrics["last_open"] == 1.11
    assert metrics["prev_close"] == 1.11


def test_put_against_returns_false():
    ok, reason, metrics = confirm_m1_micro(_bullish_last(), "put")
    assert ok is False
    assert reason == "m1_against_put"
    assert metrics["last_close"] == 1.14
    assert metrics["prev_close"] == 1.11


def test_call_aligned_returns_true():
    ok, reason, _ = confirm_m1_micro(_aligned_call(), "CALL")
    assert ok is True
    assert reason == "m1_ok"


def test_empty_candles_fail_open():
    ok, reason, metrics = confirm_m1_micro([], "call")
    assert ok is True
    assert reason == "m1_insufficient_pass"
    assert metrics["candle_count"] == 0


def test_none_candles_fail_open():
    ok, reason, _ = confirm_m1_micro(None, "put")
    assert ok is True
    assert reason == "m1_insufficient_pass"


def test_single_candle_fail_open():
    ok, reason, _ = confirm_m1_micro([_c(1.0, 1.1, 0.9, 1.05)], "call")
    assert ok is True
    assert reason == "m1_insufficient_pass"


def test_direction_case_insensitive():
    ok_call, reason_call, _ = confirm_m1_micro(_bearish_last(), "CaLl")
    ok_put, reason_put, _ = confirm_m1_micro(_bullish_last(), "PuT")
    assert ok_call is False and reason_call == "m1_against_call"
    assert ok_put is False and reason_put == "m1_against_put"


def test_put_not_blocked_when_bearish():
    # Bearish last is NOT clearly against PUT (only blocks bullish higher)
    ok, reason, _ = confirm_m1_micro(_bearish_last(), "put")
    assert ok is True
    assert reason == "m1_ok"


def test_call_not_blocked_when_bullish():
    ok, reason, _ = confirm_m1_micro(_bullish_last(), "call")
    assert ok is True
    assert reason == "m1_ok"


def test_config_enabled_by_default():
    assert cfg.M1_MICRO_CONFIRM_ENABLED is True


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


def _ok_timing() -> EntryTimingInfo:
    return EntryTimingInfo(
        ok=True,
        lag_sec=0.1,
        duration_sec=300,
        time_since_open_sec=0.1,
        secs_to_close_sec=59.9,
        decision="SYNCED_ENTRY_OPEN",
    )


@pytest.mark.asyncio
async def test_enter_trade_blocks_on_m1_against(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(ex, "_resolve_entry_timing", AsyncMock(return_value=_ok_timing()))
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    place = AsyncMock(return_value=(True, "OID-1", 1.05, 1, ""))
    monkeypatch.setattr("executor.place_order", place)
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    monkeypatch.setattr(
        "executor.fetch_candles_1m",
        AsyncMock(return_value=_bearish_last()),
    )

    ok = await ex.enter_trade(
        "EURUSD_otc", "call", 1.0, _zone(), "m1-test", "initial",
        skip_open_wait=True,
    )
    assert ok is False
    place.assert_not_awaited()
    assert bot.last_order_attempt["status"] == "failed"
    assert bot.last_order_attempt["reason"] == "m1_against_call"


@pytest.mark.asyncio
async def test_enter_trade_skips_m1_on_multi_leg(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(ex, "_resolve_entry_timing", AsyncMock(return_value=_ok_timing()))
    monkeypatch.setattr(ex, "_reconnect_if_needed", AsyncMock())
    place = AsyncMock(return_value=(True, "OID-2", 1.05, 1, ""))
    monkeypatch.setattr("executor.place_order", place)
    monkeypatch.setattr(ex, "_resolve_trade_after_expiry", AsyncMock())
    fetch = AsyncMock(return_value=_bearish_last())
    monkeypatch.setattr("executor.fetch_candles_1m", fetch)

    ok = await ex.enter_trade(
        "EURUSD_otc", "call", 1.0, _zone(), "m1-multi", "initial",
        skip_open_wait=True,
        multi_leg=True,
        register_entry_asset=False,
    )
    assert ok is True
    fetch.assert_not_awaited()
    place.assert_awaited_once()


@pytest.mark.asyncio
async def test_m1_fetch_fail_pass(monkeypatch):
    bot = _bot()
    ex = TradeExecutor(MagicMock(), bot)
    monkeypatch.setattr(
        "executor.fetch_candles_1m",
        AsyncMock(side_effect=RuntimeError("ws down")),
    )
    ok, reason = await ex._m1_micro_confirm_pre_buy("EURUSD_otc", "call")
    assert ok is True
    assert reason == "m1_fetch_fail_pass"
