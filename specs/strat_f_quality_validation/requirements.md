# Requirements — STRAT-F: calidad + validación

> Feature que cierra el trabajo de STRAT-F: filtros de calidad (#4),
> reconocimiento en backtester (#5) y validación demo en vivo (#6).
> Autorizada ejecución directa (sin puerta de aprobación humana).

## R1 — Filtro de alineación M15/M5 obligatoria
MIENTRAS se evalúa STRAT-F, el sistema DEBE rechazar la señal si el contexto
M15 no es coherente con la dirección propuesta por el fractal M5 (ej. CALL
cuando M15 está en uptrend, o PUT cuando M15 está en downtrend), registrando
la razón en el log como `[STRAT-F] <activo> skip: <razon>`.

## R2 — Filtro de payout mínimo
CUANDO un activo tiene payout < `STRAT_F_MIN_PAYOUT`, el sistema NO DEBE
evaluarlo para STRAT-F en ese ciclo.

## R3 — Filtro de edad mínima de banda/zona
CUANDO la zona/banda de Wyckoff detectada en M5 tenga menos de
`STRAT_F_ZONE_MIN_AGE` velas de antigüedad, el sistema DEBE rechazar la
señal con razón `zona muy joven`.

## R4 — Reject-first con log explícito
CUANDO la vela M1 no rechace la banda (cierra fuera o no la toca), el sistema
DEBE rechazar con razón `M1 no rechaza la banda (cierra fuera)` y NO generar
CandidateEntry.

## R5 — Refuerzo de fuerza por Fase A (ticks)
CUANDO el contexto M15 muestre clímax + absorción por ticks (`_phase_a_from_ticks`),
el sistema DEBE sumar hasta +0.15 a `strength` de la señal (sin ser gate duro).

## R6 — Score mínimo configurable
CUANDO `strength * 100 < STRAT_F_MIN_SCORE`, el sistema DEBE rechazar la señal.

## R7 — Backtester reconoce STRAT-F
CUANDO el backtester re-evalúa candidatos con `strategy_origin == 'STRAT-F'`,
el sistema DEBE aplicar `evaluate_strat_f` y reportar win rate / profit / drawdown
diferenciado por origen.

## R8 — Reporte diferenciado por origen
El sistema DEBE incluir en `Backtester.report()` una sección por estrategia
que compare STRAT-F contra STRAT-A y otras.

## R9 — Validación demo en vivo
CUANDO se ejecute el bot en PRACTICE solo con STRAT-F >= 60 min, el sistema
DEBE registrar en log señales, rechazos y entradas STRAT-F, y el resumen debe
guardarse en `progress/history.md`.

## R10 — Libro de calidad en boblioteca
El sistema DEBE incluir en `boblioteca/formacion_velas/` (o libro nuevo de
STRAT-F) un documento que explique los filtros de calidad y por qué no operar
sobre una sola vela, fundamentado en fuentes de backtesting multi-TF.

## R11 — Sin regresión de tests
CUANDO se apliquen estos cambios, el sistema DEBE mantener `pytest tests/` en verde.
