# EXP-021 — Consistencia temporal endurecida (4/5 horizontes)

## Objetivo

Medir si exigir `wins >= 4` en horizontes 1-5 mejora robustness respecto a EXP-020 (`wins >= 3`).

## Hipótesis

H1: Consistencia más estricta reduce falsos positivos y mejora robustness sin sacrificar demasiados eventos.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition.
3. Evaluar cada evento en velas idx+1 a idx+5.
4. Marcar evento como válido si gana en >=4 de 5 horizontes.
5. Evaluar resultado en próxima vela.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition
- `regla`: brake_transition=1 AND wins>=4 en horizontes 1-5

## Aislamiento

Prueba UNA condición: freno con consistencia temporal endurecida.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp021.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
