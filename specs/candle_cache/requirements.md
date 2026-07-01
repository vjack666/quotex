# Requirements — candle_cache

> Feature id=4. Caché en memoria de velas con actualización incremental.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Almacenamiento por activo y timeframe

El sistema DEBE almacenar velas en caché indexadas por `(asset, tf_sec)` como lista
ordenada por timestamp.

## R2 — Primera carga completa

CUANDO no existe entrada en caché o la entrada expiró, el sistema DEBE descargar
`lookback_count` velas completas al broker.

## R3 — Actualización incremental

CUANDO existe entrada válida en caché, el sistema DEBE solicitar solo velas
posteriores al último `ts` conocido, fusionar sin duplicados y recortar a
`lookback_count`.

## R4 — Thread-safety asyncio

El sistema DEBE proteger lecturas/escrituras del caché con `asyncio.Lock` por clave
(o lock global) para acceso concurrente seguro.

## R5 — Expiración TTL

El sistema DEBE invalidar entradas cuyo `updated_at` supere `CANDLE_CACHE_TTL_SEC`.

## R6 — Integración en prefetch

El prefetch paralelo del scanner (`fetch_candles_parallel`) DEBE usar el caché
cuando está disponible.

## R7 — Tests sin broker

Los tests DEBEN usar mocks y cubrir primera carga, actualización incremental,
expiración y acceso concurrente.