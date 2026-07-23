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
    raw_to_candle,
)


def test_raw_to_candle_maps_ticks():
    c = raw_to_candle({"time": 100, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "ticks": 495})
    assert c is not None
    assert c.ticks == 495


def test_raw_to_candle_defaults_ticks_when_absent():
    c = raw_to_candle({"time": 100, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05})
    assert c is not None
    assert c.ticks == 0


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


# ── Fix del botón del hub: reconexión real, no adorno ────────────────────────
# pyquotex SOLO re-autentica cuando session_data["token"] está vacío
# (Quotex.connect: `if not self.session_data.get("token")`). Si el socket cae por
# token rechazado, el token viejo sigue en session_data => connect() reusaría el
# token muerto y fallaría siempre. La fix limpia session_data tras el 1er fallo
# para forzar re-login. Este test demuestra que el botón YA NO es un adorno.

class _FakeClientReconnect:
    """Cliente pyquotex falso: connect() falla con token muerto la 1ra vez.

    La 1ra llamada a connect() simula token rechazado (session_data aún tiene
    token). Tras limpiar session_data (lo que hace la fix), la 2da connect()
    re-autentica y conecta OK.
    """

    def __init__(self):
        self.session_data = {"token": "DEAD_TOKEN", "cookies": "x"}
        self.api = MagicMock()
        self.api.state.SSID = "DEAD_TOKEN"
        self.connect_calls = 0

    async def close(self):
        return None

    async def connect(self):
        self.connect_calls += 1
        if self.session_data.get("token"):
            # Token muerto presente => pyquotex reusaría token y fallaría.
            return False, "Websocket connection rejected."
        # session_data vacío => re-login exitoso (comportamiento de Quotex.connect).
        self.session_data["token"] = "FRESH_TOKEN"
        self.api.state.SSID = "FRESH_TOKEN"
        return True, "connected"

    async def change_account(self, account_type):
        return None


@pytest.mark.asyncio
async def test_force_reconnect_recovers_dead_token(monkeypatch):
    """El botón del hub debe recuperar la conexión aunque el token esté muerto.

    Antes de la fix: connect() fallaba siempre (token muerto presente) => botón
    adorno. Ahora: tras el 1er fallo se limpia session_data y reconnecta.
    """
    from connection import force_reconnect

    client = _FakeClientReconnect()
    # CONNECT_RETRIES >= 2 para permitir el reintento con re-login.
    monkeypatch.setattr("connection.CONNECT_RETRIES", 3)

    ok, reason = await force_reconnect(client, "PRACTICE", step_label="hub_button")

    assert ok is True, f"El botón debió reconectar; reason={reason}"
    assert client.connect_calls >= 2, "Debió reintentar tras limpiar session_data."
    assert client.session_data.get("token") == "FRESH_TOKEN", "Re-login debió dar token nuevo."
    assert client.api.state.SSID == "FRESH_TOKEN"
