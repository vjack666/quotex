# EXP-022 — Consistencia 3/5 con evaluación alineada en idx+1

## Objetivo

Medir si evaluar el resultado en la misma vela que la consistencia (idx+1) mejora robustness respecto a EXP-020 (outcome en idx+2).

## Hipótesis

H1: La alineación entre ventana de consistencia y horizonte de evaluación reduce el desfase temporal y mejora robustness.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition.
3. Evaluar consistencia en velas idx+1 a idx+5.
4. Marcar evento como válido si gana en >=3 de 5 horizontes.
5. Evaluar resultado en vela idx+1 (alineado).
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition
- `regla`: brake_transition=1 AND wins>=3 en horizontes 1-5, outcome en idx+1

## Aislamiento

Prueba UNA condición: freno con consistencia temporal y evaluación alineada.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp022.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
