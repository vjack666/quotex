# Tasks — strat_f_maturing_m15_recheck

> Feature #16 (SDD). Checklist ejecutable. Cada task referencia al menos un R<n>.

- [ ] T1 — En `src/strat_fractal.py` añadir `recheck_m15_alignment(candles_15m, direction) -> bool` que reusa `_m15_context` y devuelve False si direction queda contra-tendencia. Cubre: R1, R2, R5.
- [ ] T2 — En `src/strat_fractal.py` añadir `stoch_m5_exhausted(stoch_k, direction) -> bool` con umbrales 20/80 (`<20` para CALL contra-M15-bajista, `>80` para PUT contra-M15-alcista). Cubre: R3.
- [ ] T3 — En `src/scanner.py`, en el bloque de promoción de `maturing_watchlist` (~líneas 2399/2351), ANTES de agendar `mark_promoted`: (a) re-evaluar `m15_context` actual del activo vía `recheck_m15_alignment`; (b) si contra-tendencia, exigir `stoch_m5_exhausted`; (c) si no hay confirmación, agendar `drop` con razón en vez de `mark_promoted`. Cubre: R1, R2, R3, R4, R5, R8.
- [ ] T4 — Confirmar en la fase de implementación que `stoch_m5` del activo está disponible en el ciclo de promoción (prefetch M5). Si no, añadir `stoch_m5: dict[str, float]` a `ScanCycleData` (sin I/O nueva). Cubre: R3 (dato).
- [ ] T5 — Verificar que el conteo Massaniello solo se incrementa en `buy()` real, no en la promoción/descarte de watchlist. Cubre: R7.
- [ ] T6 — Añadir `tests/test_strat_f_maturing_recheck.py` con casos: (a) promoción OK en tendencia alineada; (b) drop contra-tendencia SIN stoch en extremo; (c) promoción contra-tendencia CON stoch M5 en extremo. Cubre: R1, R2, R3, R4, R5.
- [ ] T7 — Ejecutar `pytest tests/` y dejar todo en verde. Cubre: trazabilidad R1-R8.
- [ ] T8 — Documentar en `progress/current.md` el mapa de trazabilidad R<n> ↔ test, y mover resumen a `progress/history.md` al cerrar.

## Trazabilidad esperada (se llena al implementar)

- R1 → T1, T3
- R2 → T1, T3
- R3 → T2, T3, T4
- R4 → T3
- R5 → T1, T3
- R6 → (sin test nuevo; ya cubierto por arquitectura de watchlist existente)
- R7 → T5
- R8 → T3
