# ADR-001 — STRAT-F como evaluador puro (no opera)

- **Estado:** Aceptado
- **Fecha:** 2026-07-11

## Contexto

La estrategia STRAT-F (Wyckoff + Fractales, M15/M5/M1) necesita decidir si
operar un par. En el repo existían dos patrones: STRAT-A (que opera dentro del
evaluador) y una tentación de meter la ejecución dentro de `evaluate_strat_f`.

## Decisión

`evaluate_strat_f(candles_15m, candles_5m, candles_1m, payout=...)` es una
**función pura**: recibe velas, devuelve `StratFEvaluation` (has_signal,
direction, zone, strength, skip_reason, m15_context, m5_event). NO conoce el
broker, NO coloca órdenes, NO toca el diario.

El `scanner` es el orquestador: llama al evaluador, acumula resultados, empuja
al HUB y graba en el diario. La ejecución la hace `consolidation_bot` /
`executor` en la fase 4/5.

## Consecuencias

- ✅ Testeable sin red (tests `test_strat_fractal.py` corren con velas sintéticas).
- ✅ Reutilizable en backtest y calibración sin efectos colaterales.
- ✅ Cumple el skill `quotex-bot-strategy` (evaluador puro + scanner-as-orchestrator).
- ⚠️ El scanner debe encargarse de TODO el side-effect (journal, hub, ejecución).
