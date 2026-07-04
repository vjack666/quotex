# Tasks — strat_a_evaluate

> Feature id=17. Marcar `[x]` al completar. Cada task referencia requirements.

---

## Tipos y función core

- [x] T1 — Añadir `PendingReversalHint`, `ScoreAdjustments` y `StratAEvaluation` en `src/strat_a.py`. Cubre: R2.
- [x] T2 — Implementar helper interno `_resolve_entry_direction()` (techo/piso/ruptura + volumen). Cubre: R6, R7, R8, R15.
- [x] T3 — Implementar `evaluate_strat_a()` con chequeo de edad de zona y `skip_zone_age_check` en rupturas. Cubre: R1, R8, R9.
- [x] T4 — Integrar validación de rebote (vela 1m, patrón, blacklist, `STRICT_PATTERN_CHECK`) y emisión de `pending_reversal_hint`. Cubre: R10, R13.
- [x] T5 — Integrar veto H1 vía parámetro `h1_trend` + `h1_confirm_enabled`. Cubre: R11.
- [x] T6 — Calcular `ScoreAdjustments` (patrón, breakout, OB, MA) y `force_execute` en el resultado. Cubre: R14.

## Scanner — delegación

- [x] T7 — Extraer helpers privados en `Scanner`: `_merge_zone_state`, `_price_sanity_ok`, `_fetch_ob_candles`, `_apply_pending_reversal_hint`, `_handle_breakout_side_effects`, `_candidate_from_strat_a_evaluation`, `_apply_score_adjustments`, `_bump_strat_a_skip_stats`. Cubre: R4, R12, R13.
- [x] T8 — Reemplazar bloque inline STRAT-A (líneas ~746–1217) por orquestación que llama `evaluate_strat_a()`; verificar ≤150 líneas en el bloque principal. Cubre: R4, R5.
- [x] T9 — Mantener fetch H1 en scanner; pasar `h1_trend` a `evaluate_strat_a`. Cubre: R11, R12.
- [x] T10 — Preservar side-effects de ruptura (journal, snapshot, `broken_zones`) solo en scanner cuando `ev.entry_mode` es breakout. Cubre: R5.

## Tests y cierre

- [x] T11 — Añadir `test_evaluate_strat_a_rebound_ceiling_put` (R6).
- [x] T12 — Añadir `test_evaluate_strat_a_rebound_floor_call` (R7).
- [x] T13 — Añadir `test_evaluate_strat_a_breakout_above_with_volume` (R8).
- [x] T14 — Añadir `test_evaluate_strat_a_breakout_below_with_volume` (R8).
- [x] T15 — Añadir `test_evaluate_strat_a_rejects_young_zone_rebound` (R9).
- [x] T16 — Añadir `test_evaluate_strat_a_no_direction_in_range_center` (R15).
- [x] T17 — Añadir `test_evaluate_strat_a_rejection_candle_emits_pending_hint` (R10).
- [x] T18 — Añadir `test_evaluate_strat_a_put_pattern_blacklisted_emits_pending_hint` (R10).
- [x] T19 — Añadir `test_evaluate_strat_a_h1_conflict_skips_signal` (R11).
- [x] T20 — Añadir `test_evaluate_strat_a_score_adjustments_on_confirmed_pattern` (R14).
- [x] T21 — Añadir/actualizar `test_strat_a_no_side_effects` para importar y ejecutar `evaluate_strat_a` sin red. Cubre: R3.
- [x] T22 — Ejecutar suite completa y `.\init.ps1`; documentar trazabilidad R→test en `progress/impl_strat_a_evaluate.md`. Cubre: R5, R16, R17.

## Verificación reviewer

- [x] T23 — Confirmar conteo ≤150 líneas bloque STRAT-A y cero regresión en tests de scanner. Cubre: R4, R5.