# Validation — EXP-048 (grilla 5x4, EURUSD REAL)

> Plantilla: docs/lab_templates/validation.md. Cumple docs/LAB_CHARTER.md
> (Art.6 congelamiento, Art.9 FDR, Art.10 dominio REAL, R12/R13).
> Este experimento cumple el Charter: Si.

## Configuracion
- extremo (oversold/overbought): 25/75
- separacion (MIN_SEPARATION): 4  (NOTA: no impacto el embudo; ver hallazgo)
- dominio: REAL (EURUSD M15), payout 0.85, seed 42

## Resultados
- nacidos: 13635
- completas (embudo): 2175
- WR: 0.5122
- EV neto: -0.5646
- p (binom vs 0.50): 0.2648
- p_adj FDR: 0.38556
- p_adj Bonferroni: 1.0

## Veredicto del tribunal
- **REFUTADA** (p_adj_fdr=0.38556 >= alpha 0.05)
- EV neto -0.5646 (negativo: el costo de payout 0.85 supera el WR).

## Hallazgo metodologico
MIN_SEPARATION (1/2/3/4) no cambio el embudo en este motor (resultados
identicos por fila de extremo). El motor de secuencia libre no aplica
separacion como filtro duro en el nacimiento. No es bug del script: es
comportamiento del motor. Se documenta para futuros experimentos.

## Reproducibilidad
- dataset_hash: sha256:fad766ea3601d827
- `python scripts/lab_exp041_060_grid.py` regenera la grilla completa.
