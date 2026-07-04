# Requirements — strat_a_evaluate

> Feature id=17. Fase SA-1 del track STRAT-A (`docs/ROADMAP_STRAT_A.md`).
> Extraer la lógica STRAT-A inline de `scanner.py` a `evaluate_strat_a()` en
> `strat_a.py`, siguiendo el patrón de `evaluate_strat_b()`.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Función pública evaluate_strat_a

El sistema DEBE exponer `evaluate_strat_a()` en `src/strat_a.py` como función
pura que recibe velas y estado precalculado (sin acceso al broker).

## R2 — Tipo de retorno StratAEvaluation

`evaluate_strat_a()` DEBE devolver un `StratAEvaluation` (dataclass) con al menos
los campos: `has_signal`, `direction`, `entry_mode`, `stage`, `zone`,
`pattern_name`, `strength`, `confirms`, `rejection_ok`, `skip_reason`,
`breakout_strength_ok`, `skip_zone_age_check`.

## R3 — Sin I/O de red en strat_a

El módulo `src/strat_a.py` NO DEBE importar `pyquotex`, `connection`, ni realizar
llamadas de red, lectura/escritura de archivos ni acceso a SQLite.

## R4 — Delegación desde scanner

CUANDO el scanner evalúa un activo con STRAT-A, el sistema DEBE delegar la
lógica de señal a `evaluate_strat_a()` y limitar la rama STRAT-A en
`scanner.py` a ≤150 líneas de orquestación (I/O, estado del bot, armado de
`CandidateEntry`).

## R5 — Regresión cero de comportamiento

CUANDO se ejecutan los tests existentes y los nuevos de `evaluate_strat_a`, el
sistema DEBE preservar el comportamiento observable actual de STRAT-A: rebotes
en techo/piso, rupturas con volumen, filtros de edad de zona, validación de vela
1m, patrones de reversión, lista negra PUT y filtro H1.

## R6 — Detección de rebote en techo

CUANDO el precio de cierre de la última vela 5m está dentro de la tolerancia
dinámica del techo de la zona, `evaluate_strat_a()` DEBE proponer
`direction="put"` y `entry_mode="rebound_ceiling"`.

## R7 — Detección de rebote en piso

CUANDO el precio de cierre de la última vela 5m está dentro de la tolerancia
dinámica del piso de la zona, `evaluate_strat_a()` DEBE proponer
`direction="call"` y `entry_mode="rebound_floor"`.

## R8 — Detección de ruptura con volumen

CUANDO la última vela 5m rompe techo o piso con cuerpo de alto volumen
(`is_high_volume_break`), `evaluate_strat_a()` DEBE proponer `stage="breakout"`,
`entry_mode` en `breakout_above` o `breakout_below`, `breakout_strength_ok=True`
y `skip_zone_age_check=True`.

## R9 — Rechazo por zona demasiado joven

CUANDO la edad de la zona es menor que el mínimo configurado para el modo de
entrada (rebote o ruptura) y `skip_zone_age_check` es falso, `evaluate_strat_a()`
DEBE devolver `has_signal=False` con `skip_reason` que identifique rechazo por
edad de zona.

## R10 — Validación de rebote (vela 1m + patrón)

CUANDO `entry_mode` es rebote, `evaluate_strat_a()` DEBE validar la vela de
rechazo 1m (`validate_rejection_candle`), el patrón 1m (`detect_reversal_pattern`
inyectado o precomputado), la fuerza mínima por dirección y la lista negra PUT;
si falla, DEBE devolver `has_signal=False` y una pista de `pending_reversal`
para que el scanner encole espera activa (sin mutar estado dentro de `strat_a`).

## R11 — Filtro H1 por entrada

CUANDO `h1_confirm_enabled=True` y `h1_trend` contradice la dirección propuesta
(bullish bloquea PUT, bearish bloquea CALL), `evaluate_strat_a()` DEBE devolver
`has_signal=False` con `skip_reason` que identifique conflicto H1.

## R12 — Entradas precalculadas OB y MA

`evaluate_strat_a()` DEBE aceptar `blocks` (order blocks precalculados) y
`ma_state` (MA precalculado) como parámetros; el fetch de velas OB y el cálculo
de MA en el scanner permanecen en la capa de análisis (I/O).

## R13 — pending_reversals permanece en scanner

El diccionario `bot.pending_reversals` y el método `_process_pending_reversals`
NO DEBEN moverse a `strat_a.py`; `evaluate_strat_a()` solo DEBE emitir
`pending_reversal_hint` cuando corresponda encolar o actualizar espera.

## R14 — Ajustes de score en el resultado

CUANDO `has_signal=True`, `evaluate_strat_a()` DEBE incluir en
`StratAEvaluation` los ajustes de score derivados de patrón 1m, ruptura, OB y MA
(equivalentes a los modificadores actuales en `scanner.py` líneas ~1148–1198).

## R15 — Sin señal en zona neutra

CUANDO el precio no está en techo, piso ni ruptura válida, `evaluate_strat_a()`
DEBE devolver `has_signal=False` con `entry_mode="none"` y sin dirección.

## R16 — Tests mínimos de evaluate_strat_a

El sistema DEBE incluir al menos 8 tests nuevos en `tests/test_strat_a.py` que
cubran escenarios de `evaluate_strat_a` (rebote, ruptura, zona joven, sin
dirección, rechazo de vela, lista negra PUT, conflicto H1, ajustes de score).

## R17 — init.ps1 en verde

CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0.