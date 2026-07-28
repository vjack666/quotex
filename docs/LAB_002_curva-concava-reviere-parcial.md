# LAB #2 — curva_concava_reviere_parcial

> script_ref: `N/A`  
> discovery_version: `discovery_v1`  
> state: `EXPERIMENTAL`

## R7 — Métricas de la ley

- **variables**: curve_shape == 'concave'  ->  reversal ~65%
- **efecto**: probabilidad de rebote = 0.6539
- **IC**: [0.3117, 0.9960]
- **walk-forward**: estado validado por hold-out (train/test por split_year); n=4848
- **p**: 0.004975
- **frecuencia**: 4848 casos estudiados (confianza HIGH)
- **markets**: forex
- **sources**: Dukascopy
- **timeframes**: M1, M5
- **state**: EXPERIMENTAL

## Explicabilidad

Ley `#2` (`curva_concava_reviere_parcial`) describe una relación estadística observada en el Atlas y validada por walk-forward. Su state actual es `EXPERIMENTAL`.

---
Documento generado por `discovery.reporter.emit_lab_doc` (Discovery Engine, Agente C).
