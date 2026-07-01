# Requirements — parallel_asset_scan

> Feature id=3. Paralelizar descarga de velas 5m y 1m en `AssetScanner.scan_all`.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Una sola llamada de activos

El sistema DEBE obtener la lista de activos OTC abiertos con una única llamada a
`get_open_assets` por ciclo de escaneo (sin re-fetch por activo).

## R2 — Prefetch paralelo 5m y 1m

El sistema DEBE descargar todas las velas 5m y 1m necesarias para el ciclo en fase
de prefetch, antes del bucle de evaluación por activo, usando `asyncio.gather` con
semáforo (`CANDLE_FETCH_CONCURRENCY`).

## R3 — Sin fetch 5m/1m en el bucle de evaluación

CUANDO `scan_all` evalúa cada activo (STRAT-A / STRAT-B), el sistema NO DEBE volver
a invocar `fetch_candles_with_retry` para timeframes 5m (300s) ni 1m (60s); debe
usar únicamente los dicts prefetched.

## R4 — Límite de concurrencia

El sistema DEBE respetar `CANDLE_FETCH_CONCURRENCY` como máximo de fetches
simultáneos al broker durante el prefetch.

## R5 — Telemetría de tiempo

El sistema DEBE registrar `scan_fetch_elapsed_ms` (tiempo total del prefetch 5m+1m)
en el log del ciclo para visibilidad de rendimiento.

## R6 — Tests sin broker

Los tests del flujo paralelo DEBEN usar mocks (sin conexión real a Quotex) y
comprobar semáforo, orden prefetch→eval y mejora de tiempo vs secuencial.