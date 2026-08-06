# Validation — EXP-067 (serie PIPELINE, EURUSD REAL)

> Plantilla: docs/lab_templates/validation.md. Cumple docs/LAB_CHARTER.md
> (Art.6 congelamiento, Art.9 FDR, Art.10 dominio REAL, R12/R13).
> Este experimento cumple el Charter: Si.

## Pipeline (estrategia de secuencia)
- `freno>separacion>extremo>martillo>cruce`
- dominio: REAL (EURUSD M15), payout 0.85, seed 42
- entrada: vela siguiente al ultimo evento del pipeline; win = expiracion 1 vela M15

## Resultados
- nacidos: 13635
- entradas: 229
- WR: 0.4934
- EV neto: -0.5806
- p (binom vs 0.50): 0.894892
- p_adj FDR: 0.000395
- p_adj Bonferroni: 1.0

## Veredicto del tribunal
- Significancia: SOBREVIVE FDR (p_adj_fdr=0.000395).
- Edge economico: NEGATIVO (pierde) (EV=-0.5806).
- El pipeline PREDICE direccion (WR != 0.50, p<0.05) pero el costo de payout
  0.85 deja EV negativo: es direccionalmente real pero economicamente perdedor.

## Reproducibilidad
- dataset_hash: sha256:0b71b12cbcdc44ac
- `python scripts/lab_exp061_070_pipeline.py` regenera la serie.
