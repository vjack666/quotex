# Tasks — refactor_monolith

> Orden de implementación. Marcar `[x]` al completar. Cada task referencia
> los requirements que cubre.

## Fase 0 — Preparación

- [x] T0 — Crear `src/config.py` con constantes operativas hoy en `consolidation_bot.py` (líneas 106–238). Cubre: R1, R13.
- [x] T1 — Extender `src/models.py` con `TradeState`, `EntryTimingInfo`, `PendingReversal`, `MartinPending`, `OrderBlock`, `MAState`. Cubre: R1, R4.
- [x] T2 — Crear `src/errors.py` con `BotError`, `ConnectionError`, `StrategyError`, `RiskError` según `docs/conventions.md`. Cubre: R2, R4.

## Fase 1 — Estrategias puras (sin I/O)

- [x] T3 — Crear `src/strat_a.py` moviendo detección de consolidación, ruptura, ATR, H1 y helpers de techo/piso. Cubre: R5, R12.
- [x] T4 — Crear `src/strat_b.py` con adaptador `candles→DataFrame` y `evaluate_strat_b` sobre `strategy_spring_sweep`. Cubre: R6, R12.
- [x] T5 — Añadir tests unitarios de estrategia en `tests/test_strat_a.py` y `tests/test_strat_b.py` (o dentro de scanner si se agrupan). Cubre: R5, R6, R12.

## Fase 2 — Conexión

- [x] T6 — Crear `src/connection.py` con `fetch_candles*`, `get_open_assets`, `connect_with_retry`, `place_order`, `looks_like_connection_issue`, `ConnectionManager.ensure_connection`. Cubre: R2.
- [x] T7 — Crear `tests/test_connection.py` con mocks de `Quotex` (camino feliz, timeout, error 403, dry-run order). Cubre: R2, R8.

## Fase 3 — Scanner

- [x] T8 — Crear `src/scanner.py` extrayendo la orquestación de `ConsolidationBot.scan_all` (fetch, evaluación, scoring, sin órdenes). Cubre: R3.
- [x] T9 — Crear `tests/test_scanner.py` con activos/velas sintéticas y mock de `connection`. Cubre: R3, R9.

## Fase 4 — Executor

- [x] T10 — Crear `src/executor.py` extrayendo `_enter`, `_resolve_trade`, martingala, ciclo, balance/risk, reconciliación. Cubre: R4.
- [x] T11 — Crear `tests/test_executor.py` con dry-run, ciclo y límites de riesgo mockeados. Cubre: R4, R10.

## Fase 5 — Facade y entrypoint

- [x] T12 — Reducir `src/consolidation_bot.py` a facade ≤500 líneas que compone `connection`, `scanner`, `executor`, `strat_a`, `strat_b`; conservar `main()` y CLI. Cubre: R1, R14.
- [x] T13 — Actualizar `main.py` para importar explícitamente `connection`, `scanner`, `executor` además de `consolidation_bot`. Cubre: R7, R13.
- [x] T14 — Añadir `test_consolidation_bot_under_500_lines` y `test_main_imports_new_modules` / smoke `--once` mockeado. Cubre: R1, R7, R14.

## Fase 6 — Verificación final

- [x] T15 — Ejecutar `python -m pytest tests/ -v` y corregir regresiones. Cubre: R8, R9, R10.
- [x] T16 — Ejecutar `.\init.ps1` hasta exit code 0. Cubre: R11.
- [x] T17 — Documentar trazabilidad `R<n> → test` en `progress/impl_refactor_monolith.md`. Cubre: R1–R14.