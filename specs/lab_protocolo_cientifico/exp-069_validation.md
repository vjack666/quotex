# Validation — EXP-069 (serie PIPELINE, EURUSD REAL)

> Plantilla: docs/lab_templates/validation.md. Cumple docs/LAB_CHARTER.md
> (Art.6 congelamiento, Art.9 FDR, Art.10 dominio REAL, R12/R13).
> Este experimento cumple el Charter: Si.

## Pipeline (estrategia de secuencia)
- `extremo>freno>cruce>martillo`
- dominio: REAL (EURUSD M15), payout 0.85, seed 42
- entrada: vela siguiente al ultimo evento del pipeline; win = expiracion 1 vela M15

## Resultados
- nacidos: 41290
- entradas: 1763
- WR: 0.5298
- EV neto: -0.5497
- p (binom vs 0.50): 0.013231
- p_adj FDR: 0.000395
- p_adj Bonferroni: 0.132308

## Veredicto del tribunal
- Significancia: SOBREVIVE FDR (p_adj_fdr=0.000395).
- Edge economico: NEGATIVO (pierde) (EV=-0.5497).
- El pipeline PREDICE direccion (WR != 0.50, p<0.05) pero el costo de payout
  0.85 deja EV negativo: es direccionalmente real pero economicamente perdedor.

## Reproducibilidad
- dataset_hash: sha256:cd486fd9f8f5a5da
- `python scripts/lab_exp061_070_pipeline.py` regenera la serie.
