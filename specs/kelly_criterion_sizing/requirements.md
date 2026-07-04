# Requirements — kelly_criterion_sizing

## R1 — Cálculo de Kelly fraccional

CUANDO el bot inicia y hay datos históricos suficientes,
EL sistema DEBE calcular el factor de Kelly fraccional usando la fórmula
`f* = (p * (b+1) - 1) / b` donde `p` = win rate histórico y
`b` = payout ratio promedio, multiplicado por la fracción configurable
(por defecto 25%).

## R2 — Win rate desde candidates

CUANDO se calcula Kelly,
EL sistema DEBE leer la tabla `candidates` de la BD del trade journal para
obtener el win rate histórico filtrando por `decision = 'ACCEPTED'` y
`outcome IN ('WIN', 'LOSS')`.

## R3 — Mínimo de trades para significancia estadística

CUANDO el número de trades históricos es menor a 10,
EL sistema DEBE devolver factor 0.0 (sin ajuste) y registrar una advertencia
en el log.

## R4 — Factor acotado

EL factor de Kelly fraccional DEBE estar acotado entre 0.0 y 1.0.
Kelly negativo (cuando el win rate no justifica operar) DEBE devolver 0.0.

## R5 — Sin datos previos o BD vacía

CUANDO no hay trades registrados o la BD no existe,
EL sistema DEBE devolver factor 0.0 sin lanzar excepción.

## R6 — Integración con Massaniello

CUANDO se calcula el factor Kelly y es mayor a 0.0,
EL sistema DEBE multiplicar `MassanielloRiskManager._initial_capital`
por dicho factor para escalar el capital de sesión.
La integración DEBE ocurrir después de la carga de pesos calibrados
y antes del primer ciclo de escaneo.

## R7 — Payout inválido

CUANDO el payout promedio leído desde la BD es cero o negativo,
EL sistema DEBE devolver factor 0.0.

## R8 — Tests

Los tests DEBEN cubrir cálculo con datos válidos, BD vacía, trades
insuficientes, Kelly negativo, payout inválido, factor acotado,
fracción personalizada, y edge cases (100% WR, 0% WR).
