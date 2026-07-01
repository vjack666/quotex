"""Tests de smc_auto_trader.py con mocks (sin broker)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models import Candle
from smc_analysis import Bias
from smc_decision_engine import Decision, Signal
from smc_auto_trader import SMCAutoTrader


def _candles(n: int) -> list[Candle]:
    return [Candle(ts=i, open=1.0, high=1.01, low=0.99, close=1.0) for i in range(n)]


@pytest.mark.asyncio
async def test_run_once_dry_wait_when_decision_wait():
    client = MagicMock()
    trader = SMCAutoTrader(client, asset="EURUSD_otc", dry_run=True)

    with patch.object(trader, "fetch_all_timeframes", AsyncMock(return_value=(_candles(20), _candles(20), _candles(20), "H4"))):
        with patch("smc_auto_trader.SMCDecisionEngine") as mock_engine_cls:
            mock_engine_cls.return_value.decide.return_value = Decision(
                signal=Signal.WAIT,
                h4_bias=Bias.NEUTRAL,
                m15_bias=Bias.NEUTRAL,
                m1_last_event=None,
                reason="esperando",
            )
            result = await trader.run_once()

    assert result.signal == Signal.WAIT
    assert result.order_placed is False


@pytest.mark.asyncio
async def test_run_once_dry_places_order_on_sell_signal():
    client = MagicMock()
    trader = SMCAutoTrader(client, asset="EURUSD_otc", dry_run=True, amount=2.0, duration=60)

    with patch.object(trader, "fetch_all_timeframes", AsyncMock(return_value=(_candles(20), _candles(20), _candles(20), "H4"))):
        with patch.object(trader, "find_open_asset", AsyncMock(return_value=("EURUSD_otc", 88))):
            with patch("smc_auto_trader.SMCDecisionEngine") as mock_engine_cls:
                mock_engine_cls.return_value.decide.return_value = Decision(
                    signal=Signal.SELL,
                    h4_bias=Bias.BEARISH,
                    m15_bias=Bias.BEARISH,
                    m1_last_event=None,
                    reason="venta",
                )
                with patch("smc_auto_trader.place_order", AsyncMock(return_value=(True, "DRY-1", 0.0, 0, ""))) as mock_place:
                    result = await trader.run_once()

    mock_place.assert_awaited_once()
    call_kwargs = mock_place.await_args.kwargs
    assert call_kwargs["dry_run"] is True
    assert mock_place.await_args.args[2] == "put"
    assert result.order_placed is True
    assert result.direction == "put"


@pytest.mark.asyncio
async def test_run_once_insufficient_candles_skips():
    client = MagicMock()
    trader = SMCAutoTrader(client)

    with patch.object(trader, "fetch_all_timeframes", AsyncMock(return_value=(_candles(3), _candles(3), _candles(3), "H4"))):
        result = await trader.run_once()

    assert result.signal == Signal.WAIT
    assert result.reason == "datos_insuficientes"


@pytest.mark.asyncio
async def test_find_open_asset_prefers_configured_symbol():
    client = MagicMock()
    trader = SMCAutoTrader(client, asset="GBPUSD_otc", min_payout=80)

    with patch("smc_auto_trader.get_open_assets", AsyncMock(return_value=[
        ("EURUSD_otc", 90),
        ("GBPUSD_otc", 85),
    ])):
        found = await trader.find_open_asset()

    assert found == ("GBPUSD_otc", 85)