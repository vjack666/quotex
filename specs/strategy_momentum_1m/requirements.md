# Requirements — strategy_momentum_1m

> Feature id=6. Estrategia momentum en velas 1m.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Detección alcista

CUANDO la última vela 1m tiene cuerpo grande vs promedio y cierre en tercio
superior, `detect_momentum_1m` DEBE devolver `("call", strength)`.

## R2 — Detección bajista

CUANDO la última vela 1m tiene cuerpo grande vs promedio y cierre en tercio
inferior, `detect_momentum_1m` DEBE devolver `("put", strength)`.

## R3 — Sin señal en condiciones débiles

CUANDO el cuerpo es pequeño o el cierre no está en el tercio extremo,
`detect_momentum_1m` DEBE devolver `None`.

## R4 — Lógica pura sin I/O

El módulo NO DEBE realizar llamadas de red ni acceder al broker.

## R5 — Integración scanner

El scanner DEBE evaluar momentum junto a STRAT-A/B y añadir candidatos con
`strategy_origin="STRAT-MOMENTUM"`.

## R6 — Tests

Los tests DEBEN cubrir momentum alcista, bajista y falso positivo.