"""Descarga paralela de velas con límite de concurrencia."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from connection import fetch_candles_with_retry
from models import Candle

if TYPE_CHECKING:
    from candle_cache import CandleCache

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
    cache: "CandleCache | None" = None,
) -> dict[str, list[Candle]]:
    """
    Descarga velas para varios símbolos en paralelo con semáforo compartido.

    Si se pasa `cache`, usa actualización incremental por activo/timeframe.
    Devuelve un dict symbol → lista de velas (puede estar vacía si falló el fetch).
    """
    if not symbols:
        return {}

    sem = asyncio.Semaphore(max(1, int(concurrency)))

    async def _fetch_one(symbol: str) -> tuple[str, list[Candle]]:
        async with sem:
            if cache is not None:
                candles = await cache.get_or_update(client, symbol, tf_sec, count)
            else:
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