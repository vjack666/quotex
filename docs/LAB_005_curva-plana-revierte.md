# LAB #5 — curva_plana_revierte

> script_ref: `N/A`  
> discovery_version: `discovery_v1`  
> state: `EXPERIMENTAL`

## R7 — Métricas de la ley

- **variables**: curve_shape == 'flat'  ->  reversal del empuje (distance_pips final < 0)
- **efecto**: probabilidad de rebote = 0.9199
- **IC**: [0.2949, 1.0000]
- **walk-forward**: estado validado por hold-out (train/test por split_year); n=1399
- **p**: 0.004975
- **frecuencia**: 1399 casos estudiados (confianza HIGH)
- **markets**: forex
- **sources**: Dukascopy
- **timeframes**: M1, M5
- **state**: EXPERIMENTAL

## Explicabilidad

Ley `#5` (`curva_plana_revierte`) describe una relación estadística observada en el Atlas y validada por walk-forward. Su state actual es `EXPERIMENTAL`.

---
Documento generado por `discovery.reporter.emit_lab_doc` (Discovery Engine, Agente C).
