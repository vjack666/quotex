# EXP-024 — Consistencia estricta 3/3 en horizontes 1-3

## Objetivo

Medir si exigir 3/3 en horizontes 1-3 mejora robustness respecto a 3/5 en horizontes 1-5.

## Hipótesis

H1: Una ventana más corta y consistencia perfecta reduce la sensibilidad a perturbaciones y mejora robustness.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition.
3. Evaluar consistencia en velas idx+1 a idx+3.
4. Marcar evento como válido si gana en 3/3 horizontes.
5. Evaluar resultado en próxima vela.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition
- `regla`: brake_transition=1 AND wins=3/3 en horizontes 1-3

## Aislamiento

Prueba UNA condición: freno con consistencia perfecta en ventana corta.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp024.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
