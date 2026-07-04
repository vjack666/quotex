# Requirements — diversification_enforcer

> Feature id=14. Límites de diversificación de trades.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Límite global de trades simultáneos

CUANDO el número de trades abiertos es >= `max_simultaneous_trades`, el sistema
DEBE rechazar cualquier nueva entrada con logging explícito de la causa.

## R2 — Spread mínimo de activos distintos

MIENTRAS hay trades abiertos, SI la cantidad de activos distintos entre ellos
es < `min_asset_spread`, ENTONCES el sistema DEBE rechazar nuevas entradas.

## R3 — Máximo de entradas concurrentes por activo

CUANDO el mismo activo ya tiene `max_entries_per_asset` entradas abiertas, el
sistema DEBE rechazar la nueva entrada.

## R4 — Rechazos loggeados

CUANDO el enforcer rechaza una entrada, el sistema DEBE escribir un log
identificable (nivel INFO o superior) con el activo, el límite violado y los
valores actuales vs permitidos.

## R5 — Cero trades abiertos

CUANDO no hay trades abiertos, el enforcer DEBE permitir la entrada sin
importar los límites configurados.

## R6 — Integración en scanner

El scanner DEBE consultar el enforcer antes de entrar cualquier trade
(STRAT-A, STRAT-B, radar, reversiones) y respetar su decisión.

## R7 — Configurable desde constants

Los tres límites (`max_simultaneous_trades`, `min_asset_spread`,
`max_entries_per_asset`) DEBEN estar definidos como constantes en
`config.py` y ser inyectados al enforcer en su constructor.
