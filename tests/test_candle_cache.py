"""Tests de candle_cache.py."""
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

from candle_cache import CandleCache
from models import Candle


def _candle(ts: int, o: float, c: float) -> Candle:
    return Candle(ts=ts, open=o, high=max(o, c) + 0.001, low=min(o, c) - 0.001, close=c)


@pytest.mark.asyncio
async def test_first_load_fetches_full_lookback(monkeypatch):
    cache = CandleCache(ttl_sec=60.0)
    full = [_candle(i * 60, 1.0, 1.01) for i in range(5)]

    monkeypatch.setattr(
        cache,
        "_full_fetch",
        AsyncMock(return_value=full),
    )

    result = await cache.get_or_update(MagicMock(), "EURUSD_otc", 60, 5)
    assert len(result) == 5
    assert result[0].ts == 0
    cache._full_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_incremental_update_merges_new_candles(monkeypatch):
    cache = CandleCache(ttl_sec=60.0)
    initial = [_candle(i * 60, 1.0, 1.01) for i in range(5)]
    incremental = initial[-2:] + [_candle(300, 1.0, 1.02), _candle(360, 1.0, 1.03)]

    fetch_mock = AsyncMock(side_effect=[initial, incremental])
    monkeypatch.setattr(cache, "_full_fetch", fetch_mock)

    client = MagicMock()
    first = await cache.get_or_update(client, "EURUSD_otc", 60, 6)
    second = await cache.get_or_update(client, "EURUSD_otc", 60, 6)

    assert len(first) == 5
    assert len(second) == 6
    assert second[-1].ts == 360
    assert fetch_mock.await_count == 2
    assert fetch_mock.await_args_list[1].args[3] <= 6


@pytest.mark.asyncio
async def test_expired_entry_triggers_full_reload(monkeypatch):
    cache = CandleCache(ttl_sec=0.01)
    batch_a = [_candle(0, 1.0, 1.01)]
    batch_b = [_candle(60, 1.0, 1.02), _candle(120, 1.0, 1.03)]

    fetch_mock = AsyncMock(side_effect=[batch_a, batch_b])
    monkeypatch.setattr(cache, "_full_fetch", fetch_mock)

    client = MagicMock()
    first = await cache.get_or_update(client, "EURUSD_otc", 60, 2)
    await asyncio.sleep(0.02)
    second = await cache.get_or_update(client, "EURUSD_otc", 60, 2)

    assert len(first) == 1
    assert len(second) == 2
    assert second[-1].ts == 120
    assert fetch_mock.await_count == 2


@pytest.mark.asyncio
async def test_concurrent_access_is_safe(monkeypatch):
    cache = CandleCache(ttl_sec=60.0)
    full = [_candle(i * 60, 1.0, 1.01) for i in range(10)]

    async def slow_fetch(client, asset, tf_sec, lookback_count):
        await asyncio.sleep(0.02)
        return list(full)

    monkeypatch.setattr(cache, "_full_fetch", slow_fetch)

    client = MagicMock()
    results = await asyncio.gather(
        *[cache.get_or_update(client, "EURUSD_otc", 60, 10) for _ in range(8)]
    )

    assert all(len(r) == 10 for r in results)
    assert all(r[-1].ts == 540 for r in results)