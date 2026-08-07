# Risks — EXP-075

> Cumple docs/LAB_CHARTER.md (Art. 4 datos inmutables, Art. 9 falsos positivos).
> Toda amenaza no mitigada se marca como bloqueante.

## Amenazas del laboratorio
| # | Amenaza | ¿Mitigada? | Cómo |
|---|---|---|---|
| 1 | Data leakage (fuga de info futura en features) | Sí | Las features de la Fase A usan solo velas ≤ i (cierre de fase). La etiqueta de resolución (move en i+H) es el OUTCOME, medido después; no entra en la construcción de la feature. |
| 2 | Look-ahead bias | Sí | Igual que arriba: split causal estricto. |
| 3 | Data snooping (probar muchas ideas hasta que una "funciona") | Sí | FDR-BH sobre los descriptores continuos (Art. 9). |
| 4 | Comparaciones múltiples | Sí | FDR-BH + Bonferroni. |
| 5 | Survivorship bias | Sí | Un solo activo EURUSD REAL; no se selecciona por performance. |
| 6 | REAL ≠ OTC | Sí | Dominio fijo REAL (Art. 10). No se promueve al Edificio con esto. |
| 7 | Muestra pequeña | Sí | n≈3308 fases >> n_min=100. |
| 8 | No independencia (fases cercanas no i.i.d.) | Parcial | Las fases son disjoint en `start`, pero hay autocorrelación temporal. Se mitiga reportando bootstrap y OOS; se anota como limitación. |
| 9 | Cambios de régimen | Sí | REDIME PRUEBA 3 de EXP-074b: split train(2022-2024) → test(2025-2026). Si el patrón continuo se mantiene OOS → robusto a régimen. |
| 10 | Overfitting | Sí | Validación OOS por split temporal; regresión con regularización leve (sklearn default). |
| 11 | Effect size irrelevante (p<α pero edge nulo) | Sí | R12 — umbral OR>1.15 por cuartil. |

## Costo operacional (R13)
| Factor | ¿Considerado? | Nota |
|---|---|---|
| Spread | N/A | Descubrimiento, no operación. |
| Slippage | N/A | — |
| Latencia | N/A | — |
| Repaint | N/A | — |
| Retraso | N/A | — |
| Payout | N/A | — |
| Comisiones | N/A | — |

Edge neto = no aplica (no es estrategia; es modelo de comportamiento del mercado).
