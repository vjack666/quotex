# Tasks — strat_a_htf_zone_wiring

> Feature id=20. Marcar `[x]` al completar. Cada task referencia requirements.

---

## htf_scanner.py — desbloqueo fetch

- [x] T1 — Cambiar import lazy en `_fetch_15m` a `connection.fetch_candles_with_retry`. Cubre: R3.
- [x] T2 — Corregir docstring de import (`from htf_scanner import HTFScanner`). Cubre: R3.

## consolidation_bot.py — lifecycle HTF

- [x] T3 — Instanciar `HTFScanner` en `ConsolidationBot.__init__` con `assets_fn` y `min_payout=STRAT_A_MIN_PAYOUT`. Cubre: R4.
- [x] T4 — Lanzar `asyncio.create_task(bot.htf_scanner.run_forever())` en `main()` tras crear el bot. Cubre: R1.
- [x] T5 — Cancelar `self._htf_task` en `shutdown_background_tasks` y bloque `finally` de `main`. Cubre: R2.

## models.py + entry_scorer.py — scoring 15m

- [x] T6 — Añadir campo `candles_15m` en `CandidateEntry`. Cubre: R14.
- [x] T7 — En `score_candidate`, preferir `entry.candles_15m` para `_score_trend` cuando `len >= 25`. Cubre: R15.

## scanner.py — gates HTF y zone_memory

- [x] T8 — Implementar `_apply_strat_a_htf_zone_gates()` reutilizando `_check_htf_available_and_aligned` y `_check_zone_memory_no_wall`. Cubre: R7, R8, R12, R16.
- [x] T9 — Invocar gates en `_scan_phase_evaluate_assets` tras `has_signal=True` y antes de `_candidate_from_strat_a_evaluation`. Cubre: R5, R6, R9.
- [x] T10 — Invocar gates en `radar_watch_tick` con el mismo contrato. Cubre: R10.
- [x] T11 — Asignar `candidate.zone_memory` y `candidate.candles_15m` tras gates exitosos. Cubre: R12, R14.
- [x] T12 — Añadir logs `⛔ [STRAT-A]` en rechazos HTF y muro zone_memory; extender `_bump_strat_a_skip_stats`. Cubre: R11.

## Tests unitarios (test_htf_zone_wiring.py)

- [x] T13 — Crear `tests/test_htf_zone_wiring.py` con `test_htf_scanner_fetch_import`. Cubre: R21.
- [x] T14 — Añadir `test_htf_veto_missing_candles`. Cubre: R17.
- [x] T15 — Añadir `test_htf_veto_misaligned_put` y `test_htf_pass_aligned_call`. Cubre: R18.
- [x] T16 — Añadir `test_zone_memory_populated_from_db` y `test_score_breakdown_zone_memory_nonzero`. Cubre: R19.
- [x] T17 — Añadir `test_zone_memory_wall_veto`. Cubre: R16.

## Tests integración (test_scanner_strat_a.py)

- [x] T18 — Añadir `test_scan_rejects_without_htf_alignment`. Cubre: R8.
- [x] T19 — Añadir `test_scan_uses_htf_cache_not_fetch`. Cubre: R5, R6, R20.

## Instrumentación y HUB (opcional P2)

- [x] T20 — Incrementar `gate_htf_reject` en vetos HTF vía `instrumentation_layer`. Cubre: R11.
- [x] T21 — Implementar `_on_htf_asset_refresh` → `hub_scanner.update_htf_status` si HUB activo.

## Cierre

- [x] T22 — Ejecutar `python -m pytest tests/ -v` y `.\init.ps1`; documentar trazabilidad R→test en `progress/impl_strat_a_htf_zone.md`. Cubre: R22, R23, R24.

## Verificación reviewer

- [x] T23 — Confirmar 0 candidatos STRAT-A sin HTF alineado; `zone_memory` y `score_breakdown` correctos en E2E; sin fetch 15m en hot path. Cubre: R7, R9, R13.