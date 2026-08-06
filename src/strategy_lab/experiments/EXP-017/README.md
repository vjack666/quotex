# EXP-017 — brake_transition con rvol>=1.5 + horizonte 4 velas

## Objetivo

Medir si combinar `rvol>=1.5` con un horizonte de 4 velas mejora la robustez del freno puro.

## Hipótesis

H1: `brake_transition` con `rvol>=1.5` evaluado en vela idx+4 tiene mayor WR y PF que variantes más cortas, porque da tiempo a que el brake se desarrolle.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, rvol.
3. Filtrar eventos: brake_transition=1 AND rvol>=1.5.
4. Evaluar resultado en vela idx+4.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, rvol
- `regla`: brake_transition=1 AND rvol>=1.5
- `horizonte`: 4 velas (idx+4)

## Aislamiento

Prueba UNA condición: freno con volumen relativo alto y horizonte extendido.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp017.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
