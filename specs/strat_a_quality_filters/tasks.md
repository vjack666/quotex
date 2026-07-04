# Tasks — strat_a_quality_filters

> Feature id=19. Marcar `[x]` al completar. Cada task referencia requirements.

---

## Configuración

- [x] T1 — Añadir `STRAT_A_MIN_PAYOUT`, `STRAT_A_MIN_SCORE` y `STRAT_A_ZONE_MIN_AGE_REBOUND` en `src/config.py`. Cubre: R1, R9.

## strat_a.py — vetos de señal

- [x] T2 — Importar constantes STRAT-A y usar `STRAT_A_ZONE_MIN_AGE_REBOUND` como default de `zone_age_rebound_min` en `evaluate_strat_a()`. Cubre: R3.
- [x] T3 — Añadir veto temprano `skip_reason="pattern_missing"` en rebotes cuando `pattern_name=="none"`. Cubre: R4.
- [x] T4 — Verificar que ninguna rama de rebote devuelve `has_signal=True` sin patrón confirmado y fuerza suficiente. Cubre: R4.

## scanner.py — filtros y logs

- [x] T5 — Excluir activos con `payout < STRAT_A_MIN_PAYOUT` del bucle STRAT-A con log `⛔ [STRAT-A]`. Cubre: R2.
- [x] T6 — Pasar `zone_age_rebound_min=STRAT_A_ZONE_MIN_AGE_REBOUND` en la llamada a `evaluate_strat_a()`. Cubre: R3.
- [x] T7 — Implementar `_log_strat_a_pattern_veto()` y usarlo en ramas `pattern_missing`, `pattern_insufficient` y `strict_pattern_veto`. Cubre: R5.
- [x] T8 — Asignar `candidate._strategy_origin = "STRAT-A"` en `_candidate_from_strat_a_evaluation` y candidatos de `_process_pending_reversals`. Cubre: R6, R8.
- [x] T9 — Actualizar `_radar_entry_from_evaluation` para usar `STRAT_A_MIN_PAYOUT`. Cubre: R2.

## entry_scorer.py — select_best

- [x] T10 — Extender `select_best()` con parámetro opcional `threshold_for: Callable[[CandidateEntry], int]`. Cubre: R6, R7, R8.
- [x] T11 — En `_scan_phase_select_execute`, invocar `select_best` con umbral efectivo `STRAT_A_MIN_SCORE` para candidatos STRAT-A y `session_threshold` para el resto; loguear vetos score STRAT-A. Cubre: R6, R7.
- [x] T12 — Asegurar que rupturas `_force_execute` STRAT-A con `score < STRAT_A_MIN_SCORE` no entran en `selected`. Cubre: R6.

## Tests unitarios (test_strat_a.py)

- [x] T13 — Añadir `test_config_strat_a_quality_constants`. Cubre: R1.
- [x] T14 — Añadir `test_evaluate_strat_a_rejects_rebound_zone_under_30min`. Cubre: R11.
- [x] T15 — Añadir `test_evaluate_strat_a_rebound_rejects_missing_pattern`. Cubre: R12.

## Tests integración (test_scanner_strat_a.py)

- [x] T16 — Añadir `test_strat_a_scan_excludes_low_payout_asset`. Cubre: R10.
- [x] T17 — Añadir `test_strat_a_select_best_uses_fixed_threshold_75`. Cubre: R13.
- [x] T18 — Añadir `test_select_best_non_strat_a_keeps_session_threshold`. Cubre: R8.

## Cierre

- [x] T19 — Ejecutar `python -m pytest tests/ -v` y `.\init.ps1`; documentar trazabilidad R→test en `progress/impl_strat_a_quality_filters.md`. Cubre: R14, R15, R16.

## Verificación reviewer

- [x] T20 — Confirmar logs de veto por payout, zona, patrón y score; sin cambio en `MIN_PAYOUT` global. Cubre: R2, R5, R9.