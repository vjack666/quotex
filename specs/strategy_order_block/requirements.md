# Requirements — strategy_order_block

> Feature id=8. Estrategia institutional Order Block en velas 1m.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Señal PUT desde OB bajista

CUANDO se detecta un Order Block bajista (última vela alcista antes de un
movimiento bajista fuerte), `detect_order_block_entry` DEBE generar `("put", strength)`
si el precio regresa al rango del OB.

## R2 — Señal CALL desde OB alcista

CUANDO se detecta un Order Block alcista (última vela bajista antes de un
movimiento alcista fuerte), `detect_order_block_entry` DEBE generar `("call", strength)`
si el precio regresa al rango del OB.

## R3 — OB mitigado no genera señal

CUANDO el precio cruza completamente el OB en dirección opuesta (cierra más
allá del lado opuesto del rango), el OB DEBE considerarse mitigado y NO generar
señal.

## R4 — Lógica pura sin I/O

La función DEBE recibir velas + OBs precalculados como entrada; NO DEBE
realizar llamadas de red ni acceder al broker.

## R5 — Integración scanner

El scanner DEBE evaluar OBs para cada activo OTC abierto y añadir candidatos
con `strategy_origin="STRAT-ORDER-BLOCK"`.

## R6 — CandidateEntry desde OB

CUANDO hay señal, el sistema DEBE crear un `CandidateEntry` con dirección,
pseudo-zone desde los extremos del OB (`price_start`, `price_end`), y score
basado en REBOUND weights.

## R7 — Reuso de detect_order_blocks existente

El módulo DEBE aceptar OBs precalculados desde el pipeline de prefetch
(reutilizando `detect_order_blocks` en `src/scan_prefetch.py`), o calcularlos
internamente si no se proveen.

## R8 — Tests

Los tests DEBEN cubrir: OB alcista → CALL, OB bajista → PUT, OB mitigado →
sin señal, sin OB → sin señal.
