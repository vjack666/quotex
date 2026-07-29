"""Serialización del fetch de velas (causa raíz cruce de respuestas 2026-07-28).

pyquotex guarda cada respuesta en un buzón compartido sin distinguir activo ni
timeframe: dos get_candles en vuelo se roban las respuestas. fetch_candles debe
serializar los pedidos (lock global) para que nunca haya dos en vuelo.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import connection  # noqa: E402


class _FakeClient:
    """Cliente falso que detecta solapamiento de pedidos en vuelo."""

    def __init__(self) -> None:
        self.in_flight = 0
        self.max_in_flight = 0

    async def get_candles(self, asset, end_time, offset, tf_sec):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.01)  # simula latencia del WebSocket
        self.in_flight -= 1
        base = 1_785_150_000
        return [
            {"time": base + i * tf_sec, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}
            for i in range(10)
        ]


def test_pedidos_concurrentes_se_serializan():
    client = _FakeClient()

    async def run():
        await asyncio.gather(*[
            connection.fetch_candles(client, f"ASSET{i}_otc", 300, 10, timeout_sec=5)
            for i in range(8)
        ])

    asyncio.run(run())
    assert client.max_in_flight == 1, (
        f"hubo {client.max_in_flight} pedidos en vuelo a la vez: "
        "los buzones compartidos de pyquotex se pisan"
    )


def test_fetch_serializado_devuelve_velas():
    client = _FakeClient()

    async def run():
        return await connection.fetch_candles(client, "EURUSD_otc", 300, 10, timeout_sec=5)

    velas = asyncio.run(run())
    assert len(velas) == 10
    assert all(b.ts - a.ts == 300 for a, b in zip(velas, velas[1:]))
