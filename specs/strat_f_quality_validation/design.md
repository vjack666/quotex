# Design — STRAT-F: calidad + validación

## Archivos a crear / modificar

- `src/config.py` — añadir `STRAT_F_ZONE_MIN_AGE` (edad mínima de zona en velas M5).
- `src/strat_fractal.py` — endurecer `evaluate_strat_f`:
  - aplicar R2 (payout) y R6 (score) como rechazos tempranos.
  - aplicar R3 (edad de zona) usando `detected_at` / conteo de barras.
  - R1 y R4 ya existen; se conservan y se loguean con razón explícita (R4 ya hace).
  - R5 ya existe (`_phase_a_from_ticks`); se documenta.
- `src/scanner.py` — el bloque STRAT-F ya llama `evaluate_strat_f`; se asegura
  que los rechazos (skip_reason) se logueen como `[STRAT-F] <activo> skip: <razon>`.
- `src/backtester.py` — añadir `'STRAT-F': evaluate_strat_f` a `STRATEGY_MAP`
  (rama genérica ya la invoca). R7/R8.
- `tests/test_strat_fractal.py` — añadir casos: payout bajo, score bajo,
  zona muy joven, alineación M15/M5. Cubre R1–R6.
- `tests/test_backtester.py` (o existente) — caso que `STRATEGY_MAP` contiene
  `'STRAT-F'` y que `reevaluate` lo procesa. Cubre R7/R8.
- `boblioteca/formacion_velas/08_calidad_filtros.md` — NUEVO. Cubre R10.
- `progress/history.md` — resumen de validación demo (R9).

## Firmas / cambios clave

- `evaluate_strat_f(candles_15m, candles_5m, candles_1m, payout, *, min_score=None, min_age=None)`
  mantiene compatibilidad: si no se pasan `min_score`/`min_age`, usa constantes de config.
- `StratFEvaluation` ya trae `skip_reason` y `m15_context`; se reutilizan.

## Alternativas descartadas

- **Gate duro de Fase A**: se descartó porque el campo `ticks` de Quotex no
  siempre viene poblado en OTC; sería gate duro mataría señales en pares donde
  `ticks=0`. Se mantiene como refuerzo de fuerza (R5), no como veto.
- **Backtest desde cero**: se descartó; el backtester ya tiene `STRATEGY_MAP` y
  rama genérica `elif origin in STRATEGY_MAP`, así que STRAT-F entra solo
  añadiendo la entrada al mapa.

## Riesgos

- El host mata procesos largos del bot completo (prefetch secundario). La
  validación demo (R9) se hace vía `progress/diag_strat_f_live.py` (corto) o
  una corrida `--hub-readonly --once`; si el host la corta, se documenta y se
  usa el diag como evidencia de señales.
