# Design — candle_cache

## Contexto

`parallel_fetch.fetch_candles_parallel` descarga el lookback completo en cada ciclo
de escaneo. Con decenas de activos esto repite trabajo innecesario.

## Solución

### `src/candle_cache.py`

```python
class CandleCache:
    async def get_or_update(client, asset, tf_sec, lookback_count) -> list[Candle]
```

- `_entries: dict[(asset, tf_sec), _CacheEntry]`
- `_locks: dict[key, asyncio.Lock]` creados bajo `_global_lock`
- `_CacheEntry(candles, updated_at)` con `updated_at = time.monotonic()`
- Merge: dict por `ts`, sort, trim `[-lookback_count:]`
- Incremental: fetch `min(lookback, CANDLE_CACHE_INCREMENTAL_COUNT)` velas recientes,
  filtrar `ts > last_ts`

### `config.py`

- `CANDLE_CACHE_TTL_SEC = 300`
- `CANDLE_CACHE_INCREMENTAL_COUNT = 8`

### Integración

- `ConsolidationBot.__init__`: `self.candle_cache = CandleCache()`
- `parallel_fetch.fetch_candles_parallel(..., cache=None)`: si `cache`, usa
  `cache.get_or_update` por símbolo
- `scanner.scan_all`: pasa `self.bot.candle_cache` al prefetch 5m/1m

## Fuera de alcance

- Persistencia en disco
- Caché para velas OB/H1 on-demand