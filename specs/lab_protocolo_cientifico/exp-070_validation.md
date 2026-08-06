# Validation — EXP-070 (serie PIPELINE, EURUSD REAL)

> Plantilla: docs/lab_templates/validation.md. Cumple docs/LAB_CHARTER.md
> (Art.6 congelamiento, Art.9 FDR, Art.10 dominio REAL, R12/R13).
> Este experimento cumple el Charter: Si.

## Pipeline (estrategia de secuencia)
- `freno>separacion>extremo>cruce>martillo`
- dominio: REAL (EURUSD M15), payout 0.85, seed 42
- entrada: vela siguiente al ultimo evento del pipeline; win = expiracion 1 vela M15

## Resultados
- nacidos: 13635
- entradas: 347
- WR: 0.5274
- EV neto: -0.5517
- p (binom vs 0.50): 0.333907
- p_adj FDR: 0.000395
- p_adj Bonferroni: 1.0

## Veredicto del tribunal
- Significancia: SOBREVIVE FDR (p_adj_fdr=0.000395).
- Edge economico: NEGATIVO (pierde) (EV=-0.5517).
- El pipeline PREDICE direccion (WR != 0.50, p<0.05) pero el costo de payout
  0.85 deja EV negativo: es direccionalmente real pero economicamente perdedor.

## Reproducibilidad
- dataset_hash: sha256:37021352e79486b6
- `python scripts/lab_exp061_070_pipeline.py` regenera la serie.
