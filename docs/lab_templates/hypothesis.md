# Hypothesis — EXP-XXX

> Plantilla estándar. Copiar a `specs/<feature>/hypothesis.md` o al contrato
> del experimento. Cumple `docs/LAB_CHARTER.md` (Art. 6 congelamiento, Art. 10
> dominio). Toda promoción requiere este documento congelado antes de Running.

## Identificación

- **ID**: EXP-XXX
- **Título**: <una frase que responda una sola pregunta>
- **Dominio**: REAL | OTC | Crypto | Índices  (Art. 10 — no mezclar)
- **Activo(s)**: EURUSD
- **Timeframe(s)**: M15 / M5 / M1
- **Tipo**: Descubrimiento (REAL) | Validación (OTC)  (Art. 10 — REAL descubre, OTC valida)

## Hipótesis

- **H0 (nula)**: <la condición no cambia el resultado>
- **H1 (alternativa)**: <la condición mejora el resultado>

## Métricas

- **Métrica primaria**: Win Rate
- **Métricas secundarias**: Profit Factor, Sharpe, Drawdown, Expectancy

## Parámetros del protocolo (se congelan en Protocol Frozen — Art. 6)

- **Nivel α**: 0.05
- **Corrección**: FDR-BH (obligatoria, Art. 9)
- **Poder esperado**: 0.80
- **n mínimo**: 500  (escenario completos)
- **Dataset**: dataset_vNNN  (hash declarado en `dataset_hash.txt`)
- **Semilla (seed)**: <entero fijo para reproducibilidad>

## Effect Size mínimo (observación Trader-Humano — R12)

- **Métrica de efecto**: WR lift | Odds Ratio | Expected Value | Sharpe
- **Umbral mínimo para promoción**: <valor>; por debajo, aunque p<α, NO se promueve.

## Declaración de cumplimiento del Charter

Este experimento cumple el Charter: Sí / No
