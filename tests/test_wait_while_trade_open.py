"""Tests for quiet wait while a trade is open (no per-second log spam)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from loop_utils import wait_while_trade_open


@pytest.mark.asyncio
async def test_wait_while_trade_open_exits_when_trade_clears(monkeypatch):
    """Trade cleared mid-wait → function exits; log.info only start + end."""
    now = {"t": 1_000_000.0}
    mono = {"t": 5_000.0}

    trade = SimpleNamespace(
        asset="XAUUSD",
        direction="call",
        opened_at=now["t"] - 10.0,
        duration_sec=60,
    )
    bot = SimpleNamespace(trades={"XAUUSD": trade})
    ticks = {"n": 0}

    def fake_time():
        return now["t"]

    def fake_monotonic():
        return mono["t"]

    async def fake_sleep(dt):
        ticks["n"] += 1
        now["t"] += float(dt)
        mono["t"] += float(dt)
        # Clear trade after a couple of quiet polls.
        if ticks["n"] >= 3:
            bot.trades = {}

    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.time.time", fake_time)
    monkeypatch.setattr("loop_utils.time.monotonic", fake_monotonic)
    monkeypatch.setattr("loop_utils.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("loop_utils.log", log_mock)
    monkeypatch.setattr("loop_utils.sys.stdout.isatty", lambda: False)

    await wait_while_trade_open(bot)

    assert bot.trades == {}
    # At most start + end — never one log per second.
    assert log_mock.info.call_count == 2
    start_msg = log_mock.info.call_args_list[0][0][0]
    end_msg = log_mock.info.call_args_list[1][0][0]
    assert "En espera de finalizar trade" in start_msg
    assert "Trade finalizado" in end_msg
    # Many quiet sleeps, but not one log per sleep.
    assert ticks["n"] >= 3
    assert log_mock.info.call_count < ticks["n"]


@pytest.mark.asyncio
async def test_wait_while_trade_open_noop_when_no_trades(monkeypatch):
    """Empty trades → return immediately without logging."""
    bot = SimpleNamespace(trades={})
    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.log", log_mock)

    await wait_while_trade_open(bot)

    assert log_mock.info.call_count == 0


@pytest.mark.asyncio
async def test_wait_while_trade_open_no_info_spam_per_second(monkeypatch):
    """Long remaining duration: many 1s sleeps, still only 2 info logs."""
    now = {"t": 2_000_000.0}

    trade = SimpleNamespace(
        asset="EURUSD_otc",
        direction="put",
        opened_at=now["t"],
        duration_sec=30,
    )
    bot = SimpleNamespace(trades={"EURUSD_otc": trade})
    sleeps = {"n": 0}

    def fake_time():
        return now["t"]

    async def fake_sleep(dt):
        sleeps["n"] += 1
        now["t"] += float(dt)
        if now["t"] >= trade.opened_at + trade.duration_sec:
            bot.trades = {}

    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.time.time", fake_time)
    monkeypatch.setattr("loop_utils.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("loop_utils.log", log_mock)
    monkeypatch.setattr("loop_utils.sys.stdout.isatty", lambda: False)

    await wait_while_trade_open(bot)

    assert sleeps["n"] >= 10  # many quiet polls
    assert log_mock.info.call_count == 2
    # No per-second info spam
    assert log_mock.info.call_count <= 2
