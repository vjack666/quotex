"""Descarga paralela de velas con límite de concurrencia."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from connection import fetch_candles_with_retry
from models import Candle

log = logging.getLogger("parallel_fetch")


async def fetch_candles_parallel(
    client: Any,
    symbols: list[str],
    tf_sec: int,
    count: int,
    *,
    concurrency: int,
    timeout_sec: float,
    retries: int = 2,
) -> dict[str, list[Candle]]:
    """
    Descarga velas para varios símbolos en paralelo con semáforo compartido.

    Devuelve un dict symbol → lista de velas (puede estar vacía si falló el fetch).
    """
    if not symbols:
        return {}

    sem = asyncio.Semaphore(max(1, int(concurrency)))

    async def _fetch_one(symbol: str) -> tuple[str, list[Candle]]:
        async with sem:
            candles = await fetch_candles_with_retry(
                client,
                symbol,
                tf_sec,
                count,
                timeout_sec=timeout_sec,
                retries=retries,
            )
        return symbol, candles

    pairs = await asyncio.gather(*(_fetch_one(sym) for sym in symbols))
    return dict(pairs)