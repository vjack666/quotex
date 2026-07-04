# Tasks — massaniello_persistence

- [x] T1 — Añadir tabla `massaniello_state` al DDL en `_ensure_schema_upgrades()` de `trade_journal.py`. Cubre: R5.
- [x] T2 — Crear `src/massaniello_persistence.py` con clase `MassanielloPersistence` (save / load / apply). Cubre: R1, R2, R3, R4, R5.
- [x] T3 — Integrar `save()` en `executor.py` tras `register_win` / `register_loss` en `_resolve_trade()`. Cubre: R1.
- [x] T4 — Integrar `load()` + `apply()` en el arranque del bot (antes del primer `can_enter()`). Cubre: R2, R3, R4.
- [x] T5 — Tests: guardado exitoso, recuperación exitosa, sin datos previos, datos corruptos. Cubre: R6.
