# Tasks — strat_a_ob_prefetch

> Feature id=21. Marcar `[x]` al completar. Cada task referencia requirements.

---

## scan_prefetch.py — blocks precalculados

- [x] T1 — Añadir `blocks_by_symbol` a `ScanCycleData`. Cubre: R4.
- [x] T2 — En `prefetch_strat_a_secondary`, calcular `blocks_by_symbol[sym] = detect_order_blocks(ob)` tras `_resolve_ob_candles`. Cubre: R5, R8.
- [x] T3 — Extender retorno de `prefetch_strat_a_secondary` con `blocks_by_symbol` (o helper testeable equivalente). Cubre: R4, R5.
- [x] T4 — Resolver import circular con lazy import o extracción mínima si pytest lo exige. Cubre: R5.

## scanner.py — consumo y limpieza

- [x] T5 — En `_scan_phase_prefetch`, recibir `blocks_by_symbol` y poblar `ScanCycleData`. Cubre: R4.
- [x] T6 — En `_scan_phase_evaluate_assets`, usar `cycle.blocks_by_symbol` en lugar de `detect_order_blocks`. Cubre: R6, R7.
- [x] T7 — Mantener `self.bot.order_blocks_by_asset[sym] = blocks` y resumen `cycle_ob_summary` con `ob_tf_label`. Cubre: R10.
- [x] T8 — Eliminar `_fetch_ob_candles` y limpiar imports huérfanos (`detect_order_blocks` si aplica). Cubre: R11.

## Tests unitarios (test_scan_prefetch.py)

- [x] T9 — Añadir `test_secondary_prefetch_populates_blocks`. Cubre: R14.
- [x] T10 — Añadir `test_blocks_match_detect_order_blocks`. Cubre: R15.
- [x] T11 — Añadir `test_ob_fallback_blocks_from_5m`. Cubre: R8, R16.
- [x] T12 — Añadir `test_ob_cache_second_call_incremental`. Cubre: R9, R17.

## Tests integración (test_scanner_strat_a.py / test_scanner.py)

- [x] T13 — Añadir `test_evaluate_phase_no_ob_network_io` (spy `tf_sec=180` en evaluate). Cubre: R3, R18.
- [x] T14 — Añadir `test_evaluate_receives_precalculated_blocks` (spy `evaluate_strat_a`). Cubre: R7, R19.
- [x] T15 — Actualizar/extender `test_scan_all_prefetches_before_eval` para paralelismo o conteos de fase. Cubre: R1, R13, R20.

## Telemetría (opcional P2)

- [x] T16 — Añadir `blocks_precalc=N` al log de fase 3b si se desea visibilidad extra. Cubre: R12.

## Refactor DRY (opcional P2)

- [ ] T17 — Refactorizar fetch OB en `prefetch_strat_a_secondary` vía `parallel_fetch.fetch_candles_parallel`. Cubre: R1 (no bloquea cierre).

## Cierre

- [x] T18 — Ejecutar `python -m pytest tests/test_scan_prefetch.py tests/test_scanner.py tests/test_scanner_strat_a.py -q` y `.\init.ps1`; documentar trazabilidad R→test en `progress/impl_strat_a_ob_prefetch.md`. Cubre: R20, R21, R22.

## Verificación reviewer

- [x] T19 — Confirmar 0 fetch OB (`tf=180`) en evaluate; blocks precalculados idénticos a regresión; `_fetch_ob_candles` ausente; radar sigue leyendo `order_blocks_by_asset`. Cubre: R3, R6, R10, R11.