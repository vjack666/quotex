# Tasks — parallel_asset_scan

## Fase 1 — Módulo de prefetch

- [x] T1 — Crear `src/parallel_fetch.py` con `fetch_candles_parallel`. Cubre: R2, R4.
- [x] T2 — Refactorizar `scan_all`: prefetch 5m+1m antes del bucle; log `scan_fetch_elapsed_ms`. Cubre: R2, R3, R5.

## Fase 2 — Tests

- [x] T3 — `test_parallel_fetch_uses_semaphore`. Cubre: R2, R4.
- [x] T4 — `test_parallel_fetch_respects_concurrency_limit`. Cubre: R4.
- [x] T5 — `test_scan_all_prefetches_before_eval` (timing + orden). Cubre: R2, R3, R6.

## Fase 3 — Verificación

- [x] T6 — Ejecutar `python -m pytest tests/ -v`. Cubre: R6.
- [x] T7 — Ejecutar `.\init.ps1` hasta exit 0. Cubre: R6.
- [x] T8 — Documentar trazabilidad en `progress/impl_parallel_asset_scan.md`. Cubre: R1–R6.