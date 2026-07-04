"""Tests de connection.py con mocks (sin broker real)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from connection import (
    connect_with_retry,
    fetch_candles,
    fetch_candles_with_retry,
    looks_like_connection_issue,
    place_order,
)


def test_looks_like_connection_issue_websocket():
    assert looks_like_connection_issue("websocket handshake failed") is True


def test_looks_like_connection_issue_unrelated():
    assert looks_like_connection_issue("invalid amount") is False


def test_looks_like_connection_issue_403():
    assert looks_like_connection_issue("HTTP 403 forbidden") is True


@pytest.mark.asyncio
async def test_fetch_candles_happy_path():
    client = MagicMock()
    client.get_candles = AsyncMock(return_value=[
        {"time": i, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}
        for i in range(5)
    ])
    candles = await fetch_candles(client, "EURUSD_otc", 60, 5)
    assert len(candles) == 5
    assert candles[0].close == 1.05
    client.get_historical_candles.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_candles_fallback_to_historical():
    client = MagicMock()
    client.get_candles = AsyncMock(return_value=[
        {"time": i, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}
        for i in range(2)
    ])
    client.get_historical_candles = AsyncMock(return_value=[
        {"time": i, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0 + i * 0.01}
        for i in range(55)
    ])
    candles = await fetch_candles(client, "EURUSD_otc", 300, 55)
    assert len(candles) == 55
    assert candles[-1].close == pytest.approx(1.54)
    client.get_historical_candles.assert_called_once_with(
        "EURUSD_otc", 55 * 300, 300, timeout=30,
    )


@pytest.mark.asyncio
async def test_fetch_candles_no_fallback_when_enough():
    client = MagicMock()
    raw = [
        {"time": i, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}
        for i in range(30)
    ]
    client.get_candles = AsyncMock(return_value=raw)
    candles = await fetch_candles(client, "EURUSD_otc", 300, 55)
    assert len(candles) == 30
    client.get_historical_candles.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_candles_timeout_returns_empty():
    client = MagicMock()
    client.get_candles = AsyncMock(side_effect=asyncio.TimeoutError())
    client.get_historical_candles = AsyncMock(side_effect=RuntimeError("historical fail"))
    candles = await fetch_candles(client, "EURUSD_otc", 60, 5)
    assert candles == []


@pytest.mark.asyncio
async def test_fetch_candles_with_retry_retries_on_too_few(monkeypatch):
    monkeypatch.setattr("connection.FETCH_RETRIES", 2)
    monkeypatch.setattr("connection.FETCH_RETRY_BACKOFF_SEC", 0.0)
    client = MagicMock()
    client.get_candles = AsyncMock(return_value=[
        {"time": i, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}
        for i in range(2)
    ])
    client.get_historical_candles = AsyncMock(side_effect=RuntimeError("historical fail"))
    candles = await fetch_candles_with_retry(
        client, "EURUSD_otc", 300, 55, timeout_sec=5.0,
    )
    assert candles == []
    assert client.get_candles.call_count == 2


@pytest.mark.asyncio
async def test_connect_with_retry_success():
    client = MagicMock()
    client.connect = AsyncMock(return_value=(True, ""))
    ok, reason = await connect_with_retry(client)
    assert ok is True
    assert reason == ""


@pytest.mark.asyncio
async def test_connect_with_retry_403_backoff(monkeypatch):
    monkeypatch.setattr("connection.CF_403_BACKOFF_SEC", 0.0)
    monkeypatch.setattr("connection.CONNECT_RETRIES", 1)
    client = MagicMock()
    client.connect = AsyncMock(return_value=(False, "403 Cloudflare"))
    ok, reason = await connect_with_retry(client)
    assert ok is False
    assert "403" in reason


@pytest.mark.asyncio
async def test_place_order_dry_run():
    client = MagicMock()
    ok, oid, price, ref, reject = await place_order(
        client, "EURUSD_otc", "call", 1.0, 30, dry_run=True,
    )
    assert ok is True
    assert oid.startswith("DRY-")
    assert reject == ""
    client.buy.assert_not_called()