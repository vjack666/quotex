"""Tests de scan_prefetch.py."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
import scan_prefetch


class FakeBotState:
    def __init__(
        self,
        *,
        trades: dict | None = None,
        greylist: set[str] | None = None,
        failed: dict[str, int] | None = None,
    ):
        self.trades = trades or {}
        self.greylist_assets = greylist or set()
        self.failed_assets = failed or {}


def _candle(ts: int, price: float) -> Candle:
    return Candle(ts=ts, open=price, high=price + 0.001, low=price - 0.001, close=price)


@pytest.mark.asyncio
async def test_prefetch_primary_returns_both_timeframes(monkeypatch):
    calls: list[tuple[str, int]] = []

    async def fake_fetch(client, symbol, tf, count, timeout_sec, retries=2):
        calls.append((symbol, tf))
        n = 20 if tf == 300 else 25
        return [_candle(i * tf, 1.1) for i in range(n)]

    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    candles_5m, candles_1m = await scan_prefetch.prefetch_primary_candles(
        MagicMock(),
        ["A_otc", "B_otc"],
        None,
        concurrency=2,
    )

    assert set(candles_5m.keys()) == {"A_otc", "B_otc"}
    assert set(candles_1m.keys()) == {"A_otc", "B_otc"}
    assert len(candles_5m["A_otc"]) == 20
    assert len(candles_1m["B_otc"]) == 25
    assert len(calls) == 4
    tfs = {tf for _, tf in calls}
    assert tfs == {300, 60}


def test_filter_scan_assets_excludes_blacklisted_greylist_trades():
    bot = FakeBotState(
        trades={"OPEN_otc": {}},
        greylist={"GREY_otc"},
        failed={"FAIL_otc": 2},
    )
    assets = [
        ("OPEN_otc", 90),
        ("GREY_otc", 88),
        ("BLACK_otc", 87),
        ("FAIL_otc", 86),
        ("OK_otc", 85),
    ]

    def is_blacklisted(sym: str) -> bool:
        return sym == "BLACK_otc"

    eligible = scan_prefetch.filter_scan_assets(assets, bot, is_blacklisted=is_blacklisted)
    assert eligible == [("OK_otc", 85)]


@pytest.mark.asyncio
async def test_secondary_prefetch_only_for_symbol_subset(monkeypatch):
    fetched_symbols: list[str] = []

    async def fake_fetch(client, symbol, tf, count, timeout_sec, retries=2):
        fetched_symbols.append(symbol)
        return [_candle(i * tf, 1.0) for i in range(10)]

    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    subset = ["SYM1_otc", "SYM3_otc"]
    candles_5m = {
        "SYM1_otc": [_candle(i, 1.0) for i in range(20)],
        "SYM2_otc": [_candle(i, 1.0) for i in range(20)],
        "SYM3_otc": [_candle(i, 1.0) for i in range(20)],
    }

    ob, h1, labels, blocks = await scan_prefetch.prefetch_strat_a_secondary(
        MagicMock(),
        subset,
        candles_5m,
        None,
        concurrency=2,
    )

    assert set(ob.keys()) == set(subset)
    assert set(h1.keys()) == set(subset)
    assert set(labels.keys()) == set(subset)
    assert set(blocks.keys()) == set(subset)
    assert fetched_symbols.count("SYM1_otc") == 2
    assert fetched_symbols.count("SYM3_otc") == 2
    assert "SYM2_otc" not in fetched_symbols


def test_symbols_needing_strat_a_prefetch_respects_min_bars():
    bot = FakeBotState()
    assets = [("SHORT_otc", 85), ("LONG_otc", 86)]
    candles_5m = {
        "SHORT_otc": [_candle(i, 1.0) for i in range(10)],
        "LONG_otc": [_candle(i, 1.0) for i in range(20)],
    }
    result = scan_prefetch.symbols_needing_strat_a_prefetch(
        assets, bot, candles_5m, is_blacklisted=lambda _: False,
    )
    assert result == ["LONG_otc"]


@pytest.mark.asyncio
async def test_secondary_prefetch_populates_blocks(monkeypatch):
    async def fake_fetch(client, symbol, tf, count, timeout_sec, retries=2):
        return [_candle(i * tf, 1.0) for i in range(10)]

    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    subset = ["SYM1_otc", "SYM2_otc"]
    candles_5m = {sym: [_candle(i, 1.0) for i in range(20)] for sym in subset}

    _ob, _h1, _labels, blocks = await scan_prefetch.prefetch_strat_a_secondary(
        MagicMock(),
        subset,
        candles_5m,
        None,
        concurrency=2,
    )

    for sym in subset:
        assert "bull" in blocks[sym]
        assert "bear" in blocks[sym]


@pytest.mark.asyncio
async def test_blocks_match_detect_order_blocks(monkeypatch):
    from strat_a import detect_order_blocks

    async def fake_fetch(client, symbol, tf, count, timeout_sec, retries=2):
        return [_candle(i * tf, 1.0) for i in range(10)]

    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    subset = ["SYM1_otc"]
    candles_5m = {sym: [_candle(i, 1.0) for i in range(20)] for sym in subset}

    ob, _h1, _labels, blocks = await scan_prefetch.prefetch_strat_a_secondary(
        MagicMock(),
        subset,
        candles_5m,
        None,
        concurrency=2,
    )

    assert blocks["SYM1_otc"] == detect_order_blocks(ob["SYM1_otc"])


@pytest.mark.asyncio
async def test_ob_fallback_blocks_from_5m(monkeypatch):
    from strat_a import detect_order_blocks

    async def fake_fetch(client, symbol, tf, count, timeout_sec, retries=2):
        if tf == 180:
            return [_candle(i, 1.0) for i in range(3)]
        return [_candle(i * tf, 1.0) for i in range(10)]

    monkeypatch.setattr(scan_prefetch, "fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    sym = "SYM_otc"
    candles_5m = {sym: [_candle(i, 1.0 + i * 0.001) for i in range(20)]}

    ob, _h1, labels, blocks = await scan_prefetch.prefetch_strat_a_secondary(
        MagicMock(),
        [sym],
        candles_5m,
        None,
        concurrency=2,
    )

    assert labels[sym] == "5m_fallback"
    assert ob[sym] == candles_5m[sym]
    assert blocks[sym] == detect_order_blocks(candles_5m[sym])


@pytest.mark.asyncio
async def test_ob_cache_second_call_incremental(monkeypatch):
    from config import ORDER_BLOCK_CANDLES, ORDER_BLOCK_TF_SEC
    from candle_cache import CandleCache

    full_fetch_calls: list[tuple[str, int, int]] = []

    async def fake_fetch(client, asset, tf_sec, count, timeout_sec=5.0, retries=2):
        if count >= ORDER_BLOCK_CANDLES:
            full_fetch_calls.append((asset, tf_sec, count))
        return [_candle(i * tf_sec, 1.0) for i in range(10)]

    monkeypatch.setattr("candle_cache.fetch_candles_with_retry", fake_fetch)
    monkeypatch.setattr(scan_prefetch, "SCAN_WS_INTER_ASSET_DELAY_SEC", 0)

    sym = "SYM_otc"
    candles_5m = {sym: [_candle(i, 1.0) for i in range(20)]}
    cache = CandleCache(ttl_sec=300.0)
    client = MagicMock()

    await scan_prefetch.prefetch_strat_a_secondary(
        client, [sym], candles_5m, cache, concurrency=2,
    )
    ob_full_fetches = [
        c for c in full_fetch_calls if c[1] == ORDER_BLOCK_TF_SEC
    ]
    assert len(ob_full_fetches) == 1

    await scan_prefetch.prefetch_strat_a_secondary(
        client, [sym], candles_5m, cache, concurrency=2,
    )
    ob_full_fetches_after = [
        c for c in full_fetch_calls if c[1] == ORDER_BLOCK_TF_SEC
    ]
    assert len(ob_full_fetches_after) == 1