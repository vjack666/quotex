# Design — parallel_asset_scan

## Contexto

`AssetScanner.scan_all` ya paralelizaba velas 5m con `create_task` + semáforo, pero
las velas 1m se descargaban de forma secuencial dentro del `for` por activo (con
`sleep(0.25)` entre activos), alargando el ciclo.

## Solución

### `src/parallel_fetch.py`

Función reutilizable:

```python
async def fetch_candles_parallel(
    client, symbols, tf_sec, count, *,
    concurrency, timeout_sec, retries=2,
) -> dict[str, list[Candle]]
```

- Crea un `asyncio.Semaphore(concurrency)` compartido.
- Lanza `_fetch_one(symbol)` por símbolo vía `asyncio.gather`.
- Cada tarea usa `fetch_candles_with_retry` de `connection.py`.

### Cambios en `src/scanner.py`

1. Tras `get_open_assets` y filtros de lista, extraer `symbols = [sym for sym, _ in assets]`.
2. Medir `time.monotonic()` y ejecutar:
   - `candles_5m_by_asset = await fetch_candles_parallel(..., TF_5M, CANDLES_LOOKBACK, ...)`
   - `candles_1m_by_asset = await fetch_candles_parallel(..., 60, 36, ...)`
3. Log: `scan_fetch_elapsed_ms=<ms>`.
4. Bucle de evaluación: `candles = candles_5m_by_asset.get(sym, [])`,
   `candles_1m = candles_1m_by_asset.get(sym, [])`.
5. Eliminar `candles_tasks`, `sleep(0.25)` pre-1m y `finally` de cancelación 5m.

### Fuera de alcance (este feature)

- Prefetch paralelo de velas OB (3m), H1 o follow-up broken-zone (siguen on-demand).
- `candle_cache` (#4): optimización incremental posterior.

## Configuración

`CANDLE_FETCH_CONCURRENCY` en `config.py` (default `2` en tests; documentación sugiere
subir en producción). No se cambia el valor por defecto en este PR salvo necesidad de test.

## Tests (`tests/test_scanner.py`)

| Test | Cubre |
|------|-------|
| `test_parallel_fetch_uses_semaphore` | R2, R4 |
| `test_parallel_fetch_respects_concurrency_limit` | R4 |
| `test_scan_all_prefetches_before_eval` | R2, R3, R5, R6 |