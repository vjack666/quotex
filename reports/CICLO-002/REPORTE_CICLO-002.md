# CICLO-002 — Validación en SPOT M15 REAL (deuda de dominio R9)

**Fecha:** 2026-08-10
**Objetivo:** validar la composición arcoíris(7-EMA) + válvula K/D en dominio
REAL (EURUSD_M15, XAUUSD_M15), no en OTC. Cierra la deuda de dominio que quedó
de EXP-076 (que midió el timing del broker en OTC 60s).

**Etiqueta de ejecución:** spot M15 REAL, ejecución SIMULADA (sin cuenta viva
del broker; no hay fills reales en esta sesión). Datos de mercado SÍ son reales
(.parquet 2004-2025 EURUSD, 2012-2025 XAUUSD).

---

## Metodología (fiel a exp_common.py del CICLO-001)

- Gate compuesto: arcoíris 7-EMA estrictamente apilado + válvula K/D
  (stoch 14,3,3; K salió del extremo; |K-D|>=DESVIO; |K-D| creciente).
- Dirección: derivada del stoch (CALL si K,D<=20; PUT si K,D>=80).
- Señal en cierre de vela M15 i. Timing broker aproximado a granularidad M15:
  entry = open[i+1] (~900s post-señal, aproxima el delay 300s del broker),
  exit = open[i+2] (entry + ~900s duración). WIN si close[exit] del lado del trade.
- Warmup 320 velas (EMAs largas). Sin lookahead: indicadores usan solo velas <= i.
- Breakeven de referencia: WR 54% (payout 85%, p bajo ese valor = ruido).

## Resultados

| Activo | DESVIO | CALL n | CALL WR | PUT n | PUT WR |
|--------|--------|--------|---------|-------|--------|
| EURUSD | 1.0 | 0 | — | 0 | — |
| EURUSD | 2.0 | 0 | — | 0 | — |
| EURUSD | 3.0 | 0 | — | 0 | — |
| EURUSD | 5.0 | 0 | — | 0 | — |
| XAUUSD | 1.0 | 0 | — | 0 | — |
| XAUUSD | 2.0 | 0 | — | 0 | — |
| XAUUSD | 3.0 | 0 | — | 0 | — |
| XAUUSD | 5.0 | 0 | — | 0 | — |

## Diagnóstico (aislamiento de variable)

Sweep previo sobre EURUSD (sin relajar otras condiciones):
- velas con dirección extrema (derive_direction != None): **146,448 / 543,310** (27%)
- solo arcoíris 7-EMA pasa: **14**
- solo válvula K/D pasa: **0**
- ambos (gate compuesto): **0**

El cuello de botella NO es DESVIO (sweep 1.0→5.0 no cambia nada): es la
condición **|K-D| creciente** de la válvula, que en M15 real no se cumple
(ni siquiera con DESVIO=1.0, donde casi cualquier separación pasaría si fuera
solo magnitud). El arcoíris estricto también es casi nulo (14/146k).

## Conclusión (honesta, falsable)

**CONCLUSIÓN = NO EVALUADA por insuficiencia de señales en dominio REAL.**

La composición arcoíris+válvula K/D, calibrada para OTC 60s, no filtra
NINGUNA operación operable en spot M15 real (n=0 en ambos activos, todos los
DESVIO). No se puede medir WR contra breakeven porque no hay muestra.

Esto NO falsa la hipótesis del edge en OTC (EXP-076/077 siguen válidos en su
dominio). Solo establece que **el gate compuesto actual no es transportable a
M15 REAL sin recalibrar la válvula** (la condición de crecimiento monótono de
|K-D| es incompatible con la dinámica de M15 real).

## Próximo paso sugerido (no ejecutado)

Para promover a REAL, la válvula K/D debe recalibrarse sobre M15 real (o
sustituirse por un filtro de separación K/D que sí ocurra en este dominio).
Eso es un NUEVO experimento (EXP-084), fuera del alcance de CICLO-002, que
queda documentado como deuda abierta de dominio.

## Archivos

- `ciclo002_spot_m15.py` — script reproducible (reusa exp_common.py)
- `_raw_results.json` — resultados crudos
