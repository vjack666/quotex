# EXP-020 — brake_transition con consistencia temporal multi-horizonte

## Objetivo

Medir si la señal del freno es consistente en múltiples horizontes temporales (1 a 5 velas), requieriendo al menos 3/5 aciertos.

## Hipótesis

H1: Un freno con consistencia multi-horizonte tiene mayor robustez que el freno evaluado en horizonte fijo.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition.
3. Para cada evento, evaluar resultado en velas idx+1 a idx+5.
4. Marcar evento como válido si gana en >=3 de 5 horizontes.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition
- `regla`: brake_transition=1 AND wins>=3 en horizontes 1-5

## Aislamiento

Prueba UNA condición: freno con consistencia temporal.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp020.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
