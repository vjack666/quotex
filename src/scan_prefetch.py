"""Orquestación de prefetch para ciclos de escaneo."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from config import (
    CANDLE_FETCH_1M_TIMEOUT_SEC,
    CANDLE_FETCH_TIMEOUT_SEC,
    CANDLES_LOOKBACK,
    H1_CANDLES_LOOKBACK,
    H1_FETCH_TIMEOUT_SEC,
    H1_TF_SEC,
    MIN_CONSOLIDATION_BARS,
    ORDER_BLOCK_CANDLES,
    ORDER_BLOCK_TF_SEC,
    SCAN_WS_INTER_ASSET_DELAY_SEC,
    TF_5M,
    TF_15M,
)
from connection import fetch_candles_with_retry
from models import Candle

if TYPE_CHECKING:
    from candle_cache import CandleCache

log = logging.getLogger("scan_prefetch")


@dataclass
class ScanCycleData:
    """Datos prefetched para un ciclo de escaneo."""

    symbols: list[str]
    assets: list[tuple[str, int]]
    candles_5m: dict[str, list[Candle]] = field(default_factory=dict)
    candles_1m: dict[str, list[Candle]] = field(default_factory=dict)
    candles_15m: dict[str, list[Candle]] = field(default_factory=dict)
    candles_ob: dict[str, list[Candle]] = field(default_factory=dict)
    candles_h1: dict[str, list[Candle]] = field(default_factory=dict)
    ob_tf_labels: dict[str, str] = field(default_factory=dict)
    blocks_by_symbol: dict[str, dict[str, list]] = field(default_factory=dict)


def filter_scan_assets(
    assets: list[tuple[str, int]],
    bot_state: Any,
    *,
    is_blacklisted: Callable[[str], bool] | None = None,
) -> list[tuple[str, int]]:
    """
    Filtra activos elegibles para evaluación (sin trades/greylist/blacklist/failed).
    """
    eligible: list[tuple[str, int]] = []
    for sym, payout in assets:
        if sym in bot_state.trades:
            continue
        if sym in bot_state.greylist_assets:
            continue
        if is_blacklisted is not None and is_blacklisted(sym):
            continue
        if sym in bot_state.failed_assets:
            continue
        eligible.append((sym, payout))
    return eligible


def symbols_needing_strat_a_prefetch(
    assets: list[tuple[str, int]],
    bot_state: Any,
    candles_5m: dict[str, list[Candle]],
    *,
    is_blacklisted: Callable[[str], bool] | None = None,
) -> list[str]:
    """Símbolos con velas 5m suficientes y filtros de skip aplicados."""
    min_bars = MIN_CONSOLIDATION_BARS + 2
    return [
        sym
        for sym, _ in filter_scan_assets(assets, bot_state, is_blacklisted=is_blacklisted)
        if len(candles_5m.get(sym, [])) >= min_bars
    ]


def decrement_failed_assets(bot_state: Any) -> None:
    """Decrementa contadores de activos en cooldown post-fallo."""
    expired_failed = [a for a, n in bot_state.failed_assets.items() if n <= 1]
    for asset in expired_failed:
        del bot_state.failed_assets[asset]
    for asset in list(bot_state.failed_assets.keys()):
        bot_state.failed_assets[asset] -= 1


async def _fetch_with_optional_stagger(
    sem: asyncio.Semaphore,
    client: Any,
    symbol: str,
    tf_sec: int,
    count: int,
    *,
    timeout_sec: float,
    cache: "CandleCache | None",
    retries: int = 2,
) -> tuple[str, int, list[Candle]]:
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
        if SCAN_WS_INTER_ASSET_DELAY_SEC > 0:
            await asyncio.sleep(SCAN_WS_INTER_ASSET_DELAY_SEC)
    return symbol, tf_sec, candles


async def prefetch_primary_candles(
    client: Any,
    symbols: list[str],
    cache: "CandleCache | None",
    concurrency: int,
    ws_sem: "asyncio.Semaphore | None" = None,
) -> tuple[dict[str, list[Candle]], dict[str, list[Candle]], dict[str, list[Candle]]]:
    """
    Descarga velas 5m y 1m en un único asyncio.gather con semáforo compartido.

    Si `ws_sem` se pasa, lo usa como semáforo de acceso al WebSocket COMPARTIDO
    con el HTF scanner (evita que ambos consumidores saturen el socket a la vez).
    Si no, crea uno nuevo con `concurrency` (retrocompatible).
    """
    if not symbols:
        return {}, {}, {}

    sem = ws_sem if ws_sem is not None else asyncio.Semaphore(max(1, int(concurrency)))
    tasks = []
    for sym in symbols:
        tasks.append(
            _fetch_with_optional_stagger(
                sem,
                client,
                sym,
                TF_5M,
                CANDLES_LOOKBACK,
                timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
                cache=cache,
            )
        )
        tasks.append(
            _fetch_with_optional_stagger(
                sem,
                client,
                sym,
                60,
                36,
                timeout_sec=CANDLE_FETCH_1M_TIMEOUT_SEC,
                cache=cache,
            )
        )
        tasks.append(
            _fetch_with_optional_stagger(
                sem,
                client,
                sym,
                TF_15M,
                120,
                timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
                cache=cache,
                retries=1,
            )
        )

    results = await asyncio.gather(*tasks)
    candles_5m: dict[str, list[Candle]] = {}
    candles_1m: dict[str, list[Candle]] = {}
    candles_15m: dict[str, list[Candle]] = {}
    for sym, tf_sec, candles in results:
        if tf_sec == TF_5M:
            candles_5m[sym] = candles
        elif tf_sec == TF_15M:
            candles_15m[sym] = candles
        else:
            candles_1m[sym] = candles
    return candles_5m, candles_1m, candles_15m


def _resolve_ob_candles(
    symbol: str,
    ob_candles: list[Candle],
    candles_5m_fallback: dict[str, list[Candle]],
) -> tuple[list[Candle], str]:
    if len(ob_candles) < 6:
        return candles_5m_fallback.get(symbol, []), "5m_fallback"
    return ob_candles, "3m"


async def prefetch_strat_a_secondary(
    client: Any,
    symbols: list[str],
    candles_5m_fallback: dict[str, list[Candle]],
    cache: "CandleCache | None",
    concurrency: int,
    ws_sem: "asyncio.Semaphore | None" = None,
) -> tuple[
    dict[str, list[Candle]],
    dict[str, list[Candle]],
    dict[str, str],
    dict[str, dict[str, list]],
]:
    """
    Prefetch paralelo de velas OB (3m) y H1 solo para el subconjunto indicado.
    Precalcula blocks_by_symbol tras resolver velas OB (incl. fallback 5m).
    """
    if not symbols:
        return {}, {}, {}, {}

    from strat_a import detect_order_blocks

    sem = ws_sem if ws_sem is not None else asyncio.Semaphore(max(1, int(concurrency)))
    tasks = []
    for sym in symbols:
        tasks.append(
            _fetch_with_optional_stagger(
                sem,
                client,
                sym,
                ORDER_BLOCK_TF_SEC,
                ORDER_BLOCK_CANDLES,
                timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
                cache=cache,
                retries=1,
            )
        )
        tasks.append(
            _fetch_with_optional_stagger(
                sem,
                client,
                sym,
                H1_TF_SEC,
                H1_CANDLES_LOOKBACK,
                timeout_sec=H1_FETCH_TIMEOUT_SEC,
                cache=cache,
            )
        )

    results = await asyncio.gather(*tasks)
    raw_ob: dict[str, list[Candle]] = {}
    candles_h1: dict[str, list[Candle]] = {}
    for sym, tf_sec, candles in results:
        if tf_sec == ORDER_BLOCK_TF_SEC:
            raw_ob[sym] = candles
        elif tf_sec == H1_TF_SEC:
            candles_h1[sym] = candles

    candles_ob: dict[str, list[Candle]] = {}
    ob_tf_labels: dict[str, str] = {}
    blocks_by_symbol: dict[str, dict[str, list]] = {}
    for sym in symbols:
        ob, label = _resolve_ob_candles(sym, raw_ob.get(sym, []), candles_5m_fallback)
        candles_ob[sym] = ob
        ob_tf_labels[sym] = label
        blocks_by_symbol[sym] = detect_order_blocks(ob)

    return candles_ob, candles_h1, ob_tf_labels, blocks_by_symbol