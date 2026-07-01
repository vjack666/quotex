# Design — entry_sync_precision

## Contexto

`TradeExecutor._sync_to_next_candle_open` mezcla cálculo, espera y validación con
tolerancia de 1.5s. Se extrae a módulo dedicado con guardia de 300ms.

## Solución

### `src/entry_sync.py`

```python
class EntrySynchronizer:
    def compute_timing(candle_open_ts: int, now: float) -> EntryTimingInfo
    async def sync_and_validate(signal_ts: int | None = None) -> EntryTimingInfo
```

- `compute_timing`: puro; `lag_sec = now - candle_open_ts`
- `sync_and_validate`: espera `next_open`, re-evalúa con `compute_timing`
- Rechazo si `lag_sec > ENTRY_MAX_LAG_SEC` o `secs_to_close <= ENTRY_REJECT_LAST_SEC`

### Cambios

- `config.py`: `ENTRY_MAX_LAG_SEC = 0.3`
- `executor.py`: delega en `EntrySynchronizer`; log explícito de timing por orden

## Alternativa descartada

Busy-polling cada 10ms — mayor CPU sin beneficio vs `asyncio.sleep` hasta open.