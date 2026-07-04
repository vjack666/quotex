# Requirements — strat_a_test_suite

> Feature id=18. Fase SA-2 del track STRAT-A (`docs/ROADMAP_STRAT_A.md`).
> Ampliar cobertura de tests del pipeline STRAT-A: unitarios de `evaluate_strat_a`,
> patrones 1m, `pending_reversals`, E2E scanner→scorer→`select_best`, integración
> executor. **Sin cambios de comportamiento en `src/`.**
> Cada `R<n>` es verificable por un test concreto.

---

## Inventario baseline (#17, ya implementado)

`tests/test_strat_a.py` contiene **15** funciones `test_*` (5 helpers legacy +
10 de `evaluate_strat_a`). Esta feature **mantiene** ese mínimo y añade tests
nuevos donde el roadmap SA-2 indica huecos.

---

## R1 — Mínimo de unitarios en test_strat_a.py

El sistema DEBE incluir al menos **15** funciones de test en
`tests/test_strat_a.py` que ejerciten lógica pura de `src/strat_a.py` sin
conexión al broker.

## R2 — Archivo E2E dedicado STRAT-A

El sistema DEBE incluir `tests/test_scanner_strat_a.py` (o archivo equivalente
acordado en `design.md`) con al menos **5** funciones de test E2E que usen
velas sintéticas y mocks de I/O (sin broker real).

## R3 — Cobertura unitaria rebote techo

CUANDO `evaluate_strat_a()` recibe precio en techo con vela 1m y patrón válidos,
un test en `tests/test_strat_a.py` DEBE verificar `has_signal=True`,
`direction="put"` y `entry_mode="rebound_ceiling"`.

## R4 — Cobertura unitaria rebote piso

CUANDO `evaluate_strat_a()` recibe precio en piso con vela 1m y patrón válidos,
un test en `tests/test_strat_a.py` DEBE verificar `has_signal=True`,
`direction="call"` y `entry_mode="rebound_floor"`.

## R5 — Cobertura unitaria ruptura

CUANDO `evaluate_strat_a()` recibe ruptura con volumen alto en techo o piso,
tests en `tests/test_strat_a.py` DEBE verificar `stage="breakout"`,
`breakout_strength_ok=True` y `entry_mode` en `breakout_above` o
`breakout_below`.

## R6 — Cobertura unitaria zona joven

CUANDO la edad de zona es menor que el mínimo de rebote,
`evaluate_strat_a()` DEBE devolver `has_signal=False` con
`skip_reason="zone_too_young"`; un test DEBE comprobarlo.

## R7 — Cobertura unitaria patrón blacklist PUT

CUANDO el patrón 1m está en `PATTERN_PUT_BLACKLIST` para una señal PUT,
`evaluate_strat_a()` DEBE devolver `has_signal=False` con
`skip_reason="put_pattern_blacklisted"` y `pending_reversal_hint` no nulo;
un test DEBE comprobarlo.

## R8 — Cobertura unitaria pending_reversal_hint

CUANDO la vela 1m no confirma el rebote, `evaluate_strat_a()` DEBE emitir
`pending_reversal_hint` con `proposed_direction` y `entry_mode` coherentes;
un test DEBE comprobarlo.

## R9 — Patrones 1m confirmados en unitarios

El sistema DEBE incluir tests en `tests/test_strat_a.py` que verifiquen
aceptación de patrón 1m con `pattern_signal` explícito para **hammer**,
**shooting_star** y **bullish_engulfing** (CALL) en escenarios de rebote válidos.

## R10 — Pending reversal: encolado en scanner

CUANDO `evaluate_strat_a()` devuelve `pending_reversal_hint`, el scanner
DEBE crear o actualizar `bot.pending_reversals[sym]`; un test E2E DEBE
verificar la entrada en el diccionario tras `_scan_phase_evaluate_assets` o
`_apply_pending_reversal_hint`.

## R11 — Pending reversal: espera activa

MIENTRAS un activo permanece en `pending_reversals` sin patrón suficiente,
`_process_pending_reversals` DEBE incrementar `scans_waited` y mantener la
entrada en el diccionario; un test DEBE comprobarlo.

## R12 — Pending reversal: confirmación

CUANDO `_process_pending_reversals` detecta patrón 1m confirmado con fuerza
suficiente y vela de rechazo válida, el sistema DEBE devolver un
`CandidateEntry` con `direction` coherente, `_from_pending=True` y eliminar
el activo de `pending_reversals`; un test DEBE comprobarlo.

## R13 — Pending reversal: expiración

CUANDO `scans_waited >= max_wait_scans` sin confirmación, `_process_pending_reversals`
DEBE eliminar el activo de `pending_reversals` sin producir candidato; un test
DEBE comprobarlo.

## R14 — Pending reversal: cancelación por precio

CUANDO el precio actual abandona el extremo de zona (techo/piso) durante la
espera, `_process_pending_reversals` DEBE eliminar el activo de
`pending_reversals`; un test DEBE comprobarlo.

## R15 — E2E scanner produce candidato puntuado

CUANDO `_scan_phase_evaluate_assets` recibe velas 5m/1m sintéticas de
consolidación con rebote válido (mocks de OB/H1/MA), el sistema DEBE añadir al
menos un `CandidateEntry` STRAT-A con `score > 0` y atributos `_entry_mode`,
`_stage` y `_reversal_pattern` poblados.

## R16 — E2E select_best sobre umbral

CUANDO `_scan_phase_select_execute` recibe candidatos STRAT-A con scores por
encima y por debajo del umbral dinámico mockeado, el sistema DEBE invocar
`select_best` y pasar a ejecución solo candidatos con `score >= umbral` (salvo
`_force_execute`); un test DEBE comprobar la selección sin broker real.

## R17 — Integración executor STRAT-A initial

CUANDO `TradeExecutor.enter_trade()` recibe `strategy_origin="STRAT-A"` y
`stage="initial"`, el sistema DEBE registrar `TradeState.strategy_origin`
como `"STRAT-A"`, `TradeState.stage` como `"initial"`, incrementar
`bot.stats["strat_a_signals"]` y crear tarea de monitor en vivo; un test DEBE
comprobarlo con mocks.

## R18 — Integración executor STRAT-A breakout

CUANDO `TradeExecutor.enter_trade()` recibe `strategy_origin="STRAT-A"` y
`stage="breakout"`, el sistema DEBE registrar `TradeState.stage` como
`"breakout"` sin crear tarea `_monitor_trade_live`; un test DEBE comprobarlo.

## R19 — Regresión cero en tests existentes

CUANDO se ejecuta `python -m pytest tests/ -v`, todos los tests existentes de
STRAT-A (incl. `test_scanner.py::test_process_pending_reversals_confirmed_pattern_no_attribute_error`)
DEBEN permanecer verdes sin modificar comportamiento de `src/`.

## R20 — Trazabilidad R→test

El implementer DEBE documentar en `progress/impl_strat_a_test_suite.md` el mapa
completo `R<n> → nombre_de_test` para cada requirement de este spec.

## R21 — init.ps1 en verde

CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0.