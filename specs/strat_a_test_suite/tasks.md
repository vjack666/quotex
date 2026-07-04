# Tasks — strat_a_test_suite

> Feature id=18. Marcar `[x]` al completar. Cada task referencia requirements.
> **Solo tests y documentación de trazabilidad; sin cambios en `src/`.**

---

## Preparación y baseline

- [x] T1 — Verificar que `tests/test_strat_a.py` tiene ≥15 funciones `test_*` y
  documentar inventario en `progress/impl_strat_a_test_suite.md`. Cubre: R1, R19.
- [x] T2 — Confirmar mapa tests existentes → R3–R8 en el mismo archivo de
  progreso. Cubre: R20.

---

## Unitarios — test_strat_a.py

- [x] T3 — Añadir `test_evaluate_strat_a_bullish_engulfing_call_rebound` con
  `pattern_signal=CandleSignal("bullish_engulfing", …, True)` en rebote piso.
  Cubre: R9.
- [x] T4 — Verificar que hammer y shooting_star siguen cubiertos por tests
  existentes (`rebound_floor_call`, `rebound_ceiling_put`); anotar en trazabilidad.
  Cubre: R3, R4, R9.

---

## E2E — tests/test_scanner_strat_a.py (nuevo archivo)

- [x] T5 — Crear `tests/test_scanner_strat_a.py` con `FakeBot`, helpers de velas
  y `_make_strat_a_scanner` (patrón `test_scanner.py`). Cubre: R2.
- [x] T6 — Añadir `test_strat_a_e2e_rebound_ceiling_produces_scored_candidate`
  vía `_scan_phase_evaluate_assets`. Cubre: R2, R3, R15.
- [x] T7 — Añadir `test_strat_a_e2e_breakout_above_sets_stage_breakout`. Cubre:
  R2, R5, R15.
- [x] T8 — Añadir `test_strat_a_e2e_young_zone_skips_candidate` (sin candidato,
  stat `rejected_young_zone`). Cubre: R2, R6, R15.
- [x] T9 — Añadir `test_strat_a_e2e_pending_hint_enqueues_reversal`. Cubre: R2,
  R8, R10.
- [x] T10 — Añadir `test_strat_a_e2e_select_best_only_above_threshold` vía
  `_scan_phase_select_execute` con umbral mockeado. Cubre: R2, R16.

---

## Pending reversals — test_scanner_strat_a.py

- [x] T11 — Añadir `test_pending_reversal_active_wait_increments_scans_waited`.
  Cubre: R11.
- [x] T12 — Añadir `test_pending_reversal_confirmed_returns_candidate_and_clears`.
  Cubre: R12.
- [x] T13 — Añadir `test_pending_reversal_expires_after_max_wait_scans`. Cubre: R13.
- [x] T14 — Añadir `test_pending_reversal_cancelled_when_price_leaves_extreme`.
  Cubre: R14.

---

## Integración executor — test_executor.py

- [x] T15 — Añadir `test_executor_enter_trade_strat_a_initial_sets_origin_and_monitor`.
  Cubre: R17.
- [x] T16 — Añadir `test_executor_enter_trade_strat_a_breakout_no_monitor`. Cubre: R18.

---

## Cierre y verificación

- [x] T17 — Completar mapa `R<n> → test` en `progress/impl_strat_a_test_suite.md`
  para R1–R21. Cubre: R20.
- [x] T18 — Ejecutar `python -m pytest tests/ -v` sin regresiones. Cubre: R19.
- [x] T19 — Ejecutar `.\init.ps1` y confirmar salida `[OK] Entorno listo`. Cubre: R21.

---

## Verificación reviewer

- [x] T20 — Confirmar `test_strat_a.py` ≥15, `test_scanner_strat_a.py` ≥5, y
  cobertura R3–R8, R10–R18 con tests nombrados en trazabilidad. Cubre: R1, R2, R20.