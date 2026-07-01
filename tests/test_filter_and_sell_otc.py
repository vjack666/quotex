"""Tests de filter_and_sell_otc.py con mocks (sin broker)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from filter_and_sell_otc import FilterSellOTC


@pytest.mark.asyncio
async def test_run_once_default_dry_run():
    client = MagicMock()
    bot = FilterSellOTC(client, min_payout=85, amount=3.0, duration=120)

    with patch.object(bot, "list_candidates", AsyncMock(return_value=[("EURUSD_otc", 92)])):
        acks = await bot.run_once()

    assert len(acks) == 1
    assert acks[0].event == "dry-run"
    assert acks[0].dry_run is True
    assert acks[0].symbol == "EURUSD_otc"
    assert acks[0].payout == 92


@pytest.mark.asyncio
async def test_run_once_picks_highest_payout_asset():
    client = MagicMock()
    bot = FilterSellOTC(client, min_payout=80)

    with patch("filter_and_sell_otc.get_open_assets", AsyncMock(return_value=[
        ("BTCUSD_otc", 95),
        ("EURUSD_otc", 88),
    ])):
        candidates = await bot.list_candidates()
        assert candidates[0] == ("BTCUSD_otc", 95)

        with patch("filter_and_sell_otc.place_order", AsyncMock(return_value=(True, "OID-1", 0.0, 0, ""))) as mock_place:
            acks = await bot.run_once(dry_run=False)

    mock_place.assert_awaited_once()
    assert mock_place.await_args.args[1] == "BTCUSD_otc"
    assert mock_place.await_args.args[2] == "put"
    assert acks[0].event == "accepted"


@pytest.mark.asyncio
async def test_run_once_empty_candidates_returns_empty():
    client = MagicMock()
    bot = FilterSellOTC(client, min_payout=99)

    with patch.object(bot, "list_candidates", AsyncMock(return_value=[])):
        acks = await bot.run_once(dry_run=True)

    assert acks == []


@pytest.mark.asyncio
async def test_list_candidates_filters_via_connection():
    client = MagicMock()
    bot = FilterSellOTC(client, min_payout=85)

    with patch("filter_and_sell_otc.get_open_assets", AsyncMock(return_value=[("USDJPY_otc", 86)])) as mock_assets:
        result = await bot.list_candidates()

    mock_assets.assert_awaited_once_with(client, 85)
    assert result == [("USDJPY_otc", 86)]