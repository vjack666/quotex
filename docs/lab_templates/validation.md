# Validation — EXP-XXX

> Plantilla estándar. Copiar a `specs/<feature>/validation.md`. Consume el
> tribunal existente (`src/strategy_lab/promotion_gate.py`):
> veredicto único PROMOVIDA | INCONCLUSIVE | REFUTADA.

## Resultados

- **Dataset**: dataset_vNNN
- **n (escenarios completos)**:
- **Win Rate**:
- **IC95%**: [ , ]
- **Profit Factor**:
- **Sharpe**:
- **Drawdown**:

## Control de falsos positivos (Art. 9)

- **FDR-BH (q)**:  (ajuste sobre múltiples comparaciones)
- **Bonferroni (α')**:  (α / n_tests)
- **p-value crudo**:
- **p-value ajustado (FDR)**:

## Poder estadístico

- **Poder observado**:
- **Poder mínimo requerido**: 0.80
- **¿Cumple poder?**: Sí / No

## Robustez

- **Bootstrap (IC del efecto)**:
- **Permutación (p empírico)**:
- **Walk-forward / out-of-sample**:
- **Stress periods**:

## Effect Size (observación Trader-Humano — R12)

- **Métrica**: WR lift | Odds Ratio | Expected Value | Sharpe
- **Valor**:
- **Umbral mínimo**:
- **¿Cumple umbral?**: Sí / No  (si No → NO se promueve aunque p<α)

## Costo operacional (observación Trader-Humano — R13)

- **Spread**:  **Slippage**:  **Latencia**:  **Repaint**:  **Retraso**:
- **Payout**:  **Comisiones**:
- **Edge bruto**:  **Edge neto** = bruto − costos:

## Veredicto (tribunal — promotion_gate.py)

- **Estado**: PROMOVIDA | INCONCLUSIVE | REFUTADA
- **Justificación**: <por qué; citar métricas y cumplimiento de Art. 6/9/10/12>
- **Dominio validado** (Art. 10): REAL | OTC | Crypto | Índices

> Una hipótesis refutada 3× en datasets independientes queda archivada
> definitivamente (Art. 12). Entre evidencias equivalentes, se prefiere la más
> simple (Art. 11).
