# EXP-016 — brake_transition con filtro de volumen relativo alto

## Objetivo

Medir si exigir `rvol` alto en el momento del freno mejora la robustez del freno puro.

## Hipótesis

H1: `brake_transition` con `rvol` alto tiene mayor WR y PF que el freno puro, porque un brake con volumen elevado es más confiable.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, rvol.
3. Filtrar eventos: brake_transition=1 AND rvol>=X.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, rvol
- `regla`: brake_transition=1 AND rvol>=X

## Aislamiento

Prueba UNA condición: freno con volumen relativo alto.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp016.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
