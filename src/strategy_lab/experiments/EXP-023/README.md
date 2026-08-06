# EXP-023 — Consistencia 3/5 con evaluación en idx+3

## Objetivo

Medir si evaluar el resultado en vela idx+3 mejora robustness respecto a EXP-020 (idx+2) y EXP-022 (idx+1).

## Hipótesis

H1: Un horizonte intermedio reduce el desfase entre señal y outcome sin perder demasiados eventos.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition.
3. Evaluar consistencia en velas idx+1 a idx+5.
4. Marcar evento como válido si gana en >=3 de 5 horizontes.
5. Evaluar resultado en vela idx+3.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition
- `regla`: brake_transition=1 AND wins>=3 en horizontes 1-5, outcome en idx+3

## Aislamiento

Prueba UNA condición: freno con consistencia temporal y evaluación en idx+3.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp023.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
