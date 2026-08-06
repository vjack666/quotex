# EXP-012 — brake_transition (1.5, 1.5) + horizonte 2 velas

## Objetivo

Medir si la combinación `body_n>=1.5`, `brake_ratio>=1.5` con horizonte de 2 velas mejora la robustez respecto a variantes más estrictas o de horizonte 1.

## Hipótesis

H1: Un filtro intermedio con horizonte extendido aumenta la muestra y la estabilidad sin hundir el WR.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, body_n, brake_ratio.
3. Filtrar eventos: brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5.
4. Evaluar resultado en vela idx+2.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, body_n, brake_ratio
- `regla`: brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5
- `horizonte`: 2 velas (idx+2)

## Aislamiento

Prueba UNA condición: freno de calidad intermedia con horizonte extendido.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp012.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
