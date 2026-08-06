# Risks — EXP-XXX

> Plantilla estándar. Copiar a `specs/<feature>/risks.md`. Declara las
> amenazas que pueden invalidar la evidencia (Art. 4 datos inmutables, Art. 9
> falsos positivos). Toda amenaza no mitigada debe marcarse como bloqueante.

## Amenazas del laboratorio

| # | Amenaza | ¿Mitigada en este EXP? | Cómo |
|---|---|---|---|
| 1 | Data leakage (fuga de información futura al entrenar) | ☐ | |
| 2 | Look-ahead bias (usar datos del futuro en el cálculo) | ☐ | |
| 3 | Data snooping (probar muchas ideas hasta que una "funciona") | ☐ | FDR-BH (Art. 9) |
| 4 | Comparaciones múltiples (falsos positivos por N tests) | ☐ | FDR-BH / Bonferroni |
| 5 | Survivorship bias (solo activos que sobrevivieron) | ☐ | |
| 6 | REAL ≠ OTC (transferir evidencia entre dominios) | ☐ | Art. 10 — dominio fijo |
| 7 | Muestra pequeña (poder < 0.80, n < mínimo) | ☐ | n mínimo declarado |
| 8 | No independencia (velas solapadas no son i.i.d.) | ☐ | |
| 9 | Cambios de régimen (el patrón murió post-muestra) | ☐ | walk-forward / robustness |
| 10 | Overfitting (memorizar la muestra, no generalizar) | ☐ | validación out-of-sample |
| 11 | Effect size irrelevante (p<α pero edge operativo nulo) | ☐ | R12 — umbral mínimo |

## Costo operacional (observación Trader-Humano — R13)

| Factor | ¿Considerado? | Nota |
|---|---|---|
| Spread | ☐ | |
| Slippage | ☐ | |
| Latencia | ☐ | |
| Repaint | ☐ | |
| Retraso (delay de señal) | ☐ | |
| Payout | ☐ | |
| Comisiones | ☐ | |

Edge neto = edge bruto − suma de costos. La promoción usa el neto.
