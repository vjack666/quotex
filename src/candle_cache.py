"""Caché en memoria de velas con actualización incremental."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from config import (
    CANDLE_CACHE_INCREMENTAL_COUNT,
    CANDLE_CACHE_TTL_SEC,
    CANDLE_FETCH_1M_TIMEOUT_SEC,
    CANDLE_FETCH_TIMEOUT_SEC,
    FETCH_RETRIES,
    TF_1M,
)
from connection import fetch_candles_with_retry
from models import Candle

log = logging.getLogger("candle_cache")

CacheKey = tuple[str, int]


@dataclass
class _CacheEntry:
    candles: list[Candle]
    updated_at: float


class CandleCache:
    """Caché asyncio-safe: clave (asset, tf_sec) → velas ordenadas por ts."""

    def __init__(self, ttl_sec: float = CANDLE_CACHE_TTL_SEC) -> None:
        self._ttl_sec = float(ttl_sec)
        self._entries: dict[CacheKey, _CacheEntry] = {}
        self._locks: dict[CacheKey, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _lock_for(self, key: CacheKey) -> asyncio.Lock:
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    def _is_stale(self, entry: _CacheEntry) -> bool:
        return (time.monotonic() - entry.updated_at) > self._ttl_sec

    @staticmethod
    def _merge_and_trim(
        existing: list[Candle],
        new_candles: list[Candle],
        lookback_count: int,
    ) -> list[Candle]:
        by_ts: dict[int, Candle] = {c.ts: c for c in existing}
        for candle in new_candles:
            by_ts[candle.ts] = candle
        merged = sorted(by_ts.values(), key=lambda c: c.ts)
        if len(merged) > lookback_count:
            merged = merged[-lookback_count:]
        return merged

    def _timeout_for_tf(self, tf_sec: int) -> float:
        return CANDLE_FETCH_1M_TIMEOUT_SEC if tf_sec <= TF_1M else CANDLE_FETCH_TIMEOUT_SEC

    async def _full_fetch(
        self,
        client: Any,
        asset: str,
        tf_sec: int,
        lookback_count: int,
    ) -> list[Candle]:
        return await fetch_candles_with_retry(
            client,
            asset,
            tf_sec,
            lookback_count,
            timeout_sec=self._timeout_for_tf(tf_sec),
            retries=FETCH_RETRIES,
        )

    async def get_or_update(
        self,
        client: Any,
        asset: str,
        tf_sec: int,
        lookback_count: int,
    ) -> list[Candle]:
        """
        Devuelve velas del caché, actualizando incrementalmente si es posible.

        Primera carga o entrada expirada: fetch completo.
        Hit válido: fetch reciente y fusiona solo velas con ts > último conocido.
        """
        key = (asset, tf_sec)
        lock = await self._lock_for(key)
        async with lock:
            entry = self._entries.get(key)
            if entry is None or self._is_stale(entry) or not entry.candles:
                candles = await self._full_fetch(client, asset, tf_sec, lookback_count)
                self._entries[key] = _CacheEntry(
                    candles=list(candles),
                    updated_at=time.monotonic(),
                )
                log.debug(
                    "%s tf=%ss: caché MISS — carga completa (%d velas)",
                    asset,
                    tf_sec,
                    len(candles),
                )
                return list(candles)

            last_ts = entry.candles[-1].ts
            incremental_count = min(
                lookback_count,
                max(3, int(CANDLE_CACHE_INCREMENTAL_COUNT)),
            )
            fetched = await self._full_fetch(
                client,
                asset,
                tf_sec,
                incremental_count,
            )
            newer = [c for c in fetched if c.ts > last_ts]
            if newer:
                merged = self._merge_and_trim(entry.candles, newer, lookback_count)
                self._entries[key] = _CacheEntry(
                    candles=merged,
                    updated_at=time.monotonic(),
                )
                log.debug(
                    "%s tf=%ss: caché HIT incremental +%d velas (total=%d)",
                    asset,
                    tf_sec,
                    len(newer),
                    len(merged),
                )
                return list(merged)

            entry.updated_at = time.monotonic()
            log.debug(
                "%s tf=%ss: caché HIT sin velas nuevas (total=%d)",
                asset,
                tf_sec,
                len(entry.candles),
            )
            return list(entry.candles)

    def expire_stale(self) -> int:
        """Elimina entradas expiradas. Devuelve cantidad purgada."""
        now = time.monotonic()
        stale_keys = [
            key
            for key, entry in self._entries.items()
            if (now - entry.updated_at) > self._ttl_sec
        ]
        for key in stale_keys:
            self._entries.pop(key, None)
            self._locks.pop(key, None)
        return len(stale_keys)

    def clear(self) -> None:
        self._entries.clear()
        self._locks.clear()