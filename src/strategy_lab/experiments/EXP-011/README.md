# EXP-011 — brake_transition alta calidad + horizonte 2 velas

## Objetivo

Medir el impacto de ampliar el horizonte de evaluación a 2 velas después del freno, manteniendo los filtros de calidad `body_n` y `brake_ratio` altos.

## Hipótesis

H1: Extender el horizonte a 2 velas aumenta la robustez de la señal del freno puro sin reducir excesivamente los eventos.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, body_n, brake_ratio.
3. Filtrar eventos: brake_transition=1 AND body_n>=2.0 AND brake_ratio>=2.0.
4. Evaluar resultado en vela idx+2.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, body_n, brake_ratio
- `regla`: brake_transition=1 AND body_n>=2.0 AND brake_ratio>=2.0
- `horizonte`: 2 velas (idx+2)

## Aislamiento

Prueba UNA condición: freno de alta calidad con horizonte extendido.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp011.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
