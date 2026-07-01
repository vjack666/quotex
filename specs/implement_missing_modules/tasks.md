# Tasks — implement_missing_modules

## Fase 1 — Análisis y decisión

- [x] T1 — Crear `src/smc_analysis.py` adaptado desde QUOTEX con `models.Candle`. Cubre: R1, R5.
- [x] T2 — Crear `src/smc_decision_engine.py` con `SMCDecisionEngine.decide()`. Cubre: R2, R5.
- [x] T3 — Tests `tests/test_smc_analysis.py` y `tests/test_smc_decision_engine.py`. Cubre: R6.

## Fase 2 — Traders

- [x] T4 — Crear `src/smc_auto_trader.py` con `SMCAutoTrader.run_once/run_loop`. Cubre: R3, R5.
- [x] T5 — Crear `src/filter_and_sell_otc.py` con `FilterSellOTC.run_once`. Cubre: R4, R5.
- [x] T6 — Tests `tests/test_smc_auto_trader.py` y `tests/test_filter_and_sell_otc.py`. Cubre: R6.

## Fase 3 — Verificación

- [x] T7 — Ejecutar `python -m pytest tests/ -v`. Cubre: R7.
- [x] T8 — Ejecutar `.\init.ps1` hasta exit 0. Cubre: R7.
- [x] T9 — Documentar trazabilidad en `progress/impl_implement_missing_modules.md`. Cubre: R1–R7.