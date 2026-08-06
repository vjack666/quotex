# EXP-014 — brake_transition (1.5, 1.5) + horizonte 3 velas

## Objetivo

Medir si evaluar en vela idx+3 mejora la robustez respecto a horizonte 1 y 2 con el mismo filtro intermedio.

## Hipótesis

H1: Un horizonte de 3 velas aumenta la estabilidad del resultado sin reducir excesivamente los eventos.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, body_n, brake_ratio.
3. Filtrar eventos: brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5.
4. Evaluar resultado en vela idx+3.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, body_n, brake_ratio
- `regla`: brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5
- `horizonte`: 3 velas (idx+3)

## Aislamiento

Prueba UNA condición: freno de calidad intermedia con horizonte extendido a 3 velas.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp014.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
