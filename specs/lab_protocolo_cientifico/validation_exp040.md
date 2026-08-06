# Validation — EXP-040 (embudo del Edificio sobre EURUSD REAL)

> Plantilla: `docs/lab_templates/validation.md`. Cumple `docs/LAB_CHARTER.md`.
> Este experimento cumple el Charter: **Sí** (protocolo congelado Art.6,
> FDR Art.9, dominio REAL Art.10, Effect Size + Costo reportados).

## Veredicto del tribunal

- **Veredicto global**: INCONCLUSIVE (win_rate 0.523, p=0.077 > α, EV -0.556).
- **Veredicto por firma (FDR ajustado, n≥100)**: 0 firmas promovibles.

## Métricas (Art. 3 + Effect Size R12 + Costo R13)

| Firma | n | WR | p (crudo) | p_adj FDR | Odds Ratio | EV neto (payout 0.85) | Promovible |
|-------|---|----|-----------|-----------|-----------|----------------------|------------|
| freno>separacion>extremo>cruce>martillo | 169 | 0.5799 | 0.0452 | 0.1807 | 1.38 | **-0.5071** | No (EV<0) |
| extremo>freno>separacion>martillo>cruce | 274 | 0.5401 | 0.2045 | 0.1807 | 1.18 | -0.5409 | No |
| freno>separacion>extremo>martillo>cruce | 188 | 0.5160 | 0.7155 | 0.1807 | 1.07 | -0.5614 | No |
| extremo>freno>separacion>cruce>martillo | 492 | 0.4939 | 0.8217 | 0.1807 | 0.98 | -0.5802 | No |

## Interpretación (lenguaje trader)

El embudo NO es rescatable "en promedio" ni por la mejor secuencia aislada:
- WR máxima 0.58 suena bien, pero con payout 0.85 el **expected value es
  negativo** (−0.50 por trade). Operarlo destruye capital.
- La firma con mejor WR (0.58) tiene p=0.045 crudo, pero tras FDR pasa a
  0.18 → deja de ser significativa. Es ruido, no señal.
- Conclusión del Charter: **no se promueve ninguna configuración del Edificio
  desde EURUSD REAL**. Esto previene exactamente el error de las 36 firmas
  falsas que motivaron el Art. 9.

## Qué NO se hizo (disciplina metodológica)

- NO se aflojó el freno a ojo para "que entren más".
- NO se promovió la firma de WR 0.58 ignorando el costo (EV negativo).
- NO se mezcló REAL con OTC.

## Próximo paso sugerido (evolución, no bloquea)

1. Probar payout REAL de Quotex (¿0.90? cambia el EV). Si con payout 0.90
   alguna firma da EV>0 y FDR significativo, re-evaluar.
2. El embudo REAL (40→2→0→0 de EXP-039) es el del Edificio EN VIVO, que usa
   el freno de la caja negra (`EDIFICIO_BRAKE_CONFIRM_RATIO`), DISTINTO al
   freno estocástico de este motor. Para atacar EXP-039 de raíz falta un
   experimento que varié `EDIFICIO_BRAKE_CONFIRM_RATIO` sobre histórico.
3. ADR-002: cualquier candidato debe re-validarse en OTC antes de promover.

## Reproducibilidad

- seed=42, dataset_hash=sha256:ae0f88089bb47eca
- `python scripts/lab_exp040_embudo.py` → reports/EXP-040/ (summary.md,
  firma_analysis.csv, seed.txt, environment.txt, dataset_hash.txt,
  protocol_frozen.json, lifecycle.json).
