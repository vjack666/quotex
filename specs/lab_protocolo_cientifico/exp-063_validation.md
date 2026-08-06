# Validation — EXP-063 (serie PIPELINE, EURUSD REAL)

> Plantilla: docs/lab_templates/validation.md. Cumple docs/LAB_CHARTER.md
> (Art.6 congelamiento, Art.9 FDR, Art.10 dominio REAL, R12/R13).
> Este experimento cumple el Charter: Si.

## Pipeline (estrategia de secuencia)
- `freno>extremo>cruce`
- dominio: REAL (EURUSD M15), payout 0.85, seed 42
- entrada: vela siguiente al ultimo evento del pipeline; win = expiracion 1 vela M15

## Resultados
- nacidos: 13635
- entradas: 2178
- WR: 0.523
- EV neto: -0.5555
- p (binom vs 0.50): 0.033871
- p_adj FDR: 0.000395
- p_adj Bonferroni: 0.33871

## Veredicto del tribunal
- Significancia: SOBREVIVE FDR (p_adj_fdr=0.000395).
- Edge economico: NEGATIVO (pierde) (EV=-0.5555).
- El pipeline PREDICE direccion (WR != 0.50, p<0.05) pero el costo de payout
  0.85 deja EV negativo: es direccionalmente real pero economicamente perdedor.

## Reproducibilidad
- dataset_hash: sha256:ff5882d1eaa06f07
- `python scripts/lab_exp061_070_pipeline.py` regenera la serie.
