# Requirements — massaniello_persistence

## R1 — Guardar estado post-operación

CUANDO una operación Massaniello termina (WIN/LOSS),
EL sistema DEBE guardar el estado completo de `MassanielloRiskManager` en SQLite.

## R2 — Recuperar estado al iniciar

CUANDO el bot inicia,
EL sistema DEBE cargar el último estado Massaniello guardado desde la BD.

## R3 — Valores por defecto sin datos previos

CUANDO no hay estado previo en la BD,
EL sistema DEBE iniciar con valores por defecto (5 ops / 3 ITM).

## R4 — Datos corruptos o inválidos

CUANDO el estado guardado está corrupto o es inválido,
EL sistema DEBE iniciar con valores por defecto y registrar una advertencia en el log.

## R5 — Campos del estado

El estado guardado DEBE incluir: `operations`, `expected_wins`, `session_max_min`, `session_start_time`, `entries`, `wins`, `losses`, `current_balance`, `initial_capital`.

## R6 — Tests

Los tests DEBEN cubrir guardado exitoso, recuperación exitosa, ausencia de datos previos y datos corruptos.
