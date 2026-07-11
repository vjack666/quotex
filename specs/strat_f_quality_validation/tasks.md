# Tasks — STRAT-F: calidad + validación

- [x] T1 — Añadir `STRAT_F_ZONE_MIN_AGE` en `src/config.py`. Cubre: R3.
- [x] T2 — Endurecer `evaluate_strat_f` (payout R2, score R6, edad zona R3).
        Usar `min_score`/`min_age` con fallback a config. Cubre: R1, R2, R3, R6.
- [x] T3 — Verificar log de rechazos `[STRAT-F] skip:` con razón explícita. Cubre: R1, R4.
- [x] T4 — Añadir rama `_reevaluate_strat_f` + STRAT-F a `origins` en backtester. Cubre: R7.
- [x] T5 — `Backtester.report()` itera por origen; STRAT-F incluido. Cubre: R8.
- [x] T6 — Tests `test_strat_fractal.py`: payout bajo, score bajo, zona joven,
        alineación M15/M5. Cubre: R1–R6.
- [x] T7 — Test backtester: STRAT-F reconocido y `reevaluate` lo procesa. Cubre: R7, R8.
- [x] T8 — Libro `boblioteca/formacion_velas/08_calidad_filtros.md`. Cubre: R10.
- [x] T9 — `pytest tests/` → 267 passed. Cubre: R11.
- [x] T10 — Validación demo vía `diag_strat_f_live.py` → `progress/diag_strat_f_filters.log`
         (1 señal limpia USDPKR_otc, 6 filtros en acción). Resumen en `progress/history.md`. Cubre: R9.
- [x] T11 — `feature_list.json` (#1–#6 → done) + `docs/ROADMAP.md` actualizados. Cubre: cierre.
