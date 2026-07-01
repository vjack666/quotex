# Requirements — entry_sync_precision

> Feature id=5. Sincronización precisa con apertura de vela 1m.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Timing guard estricto

El sistema DEBE rechazar órdenes cuyo lag desde la apertura de vela supere
`ENTRY_MAX_LAG_SEC` (0.3s).

## R2 — Cálculo de timing puro

El módulo DEBE exponer `compute_timing(candle_open_ts, now) → EntryTimingInfo`
sin efectos secundarios (sin sleep ni I/O).

## R3 — Sincronización a apertura

CUANDO `ENTRY_SYNC_TO_CANDLE` está activo, el executor DEBE esperar al próximo
open de vela 1m antes de enviar la orden.

## R4 — Logging por orden

El sistema DEBE registrar `time_since_open` y `secs_to_close` por cada intento
de entrada.

## R5 — Tests

Los tests DEBEN cubrir aceptación, rechazo por lag y sync deshabilitado.