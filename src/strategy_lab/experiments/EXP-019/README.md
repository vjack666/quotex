# EXP-019 — brake_transition con score combinado body_n * brake_ratio

## Objetivo

Medir si usar el producto `body_n * brake_ratio` como score único mejora la robustez respecto a umbrales separados.

## Hipótesis

H1: El score combinado captura una interacción no lineal que mejora WR y PF sin sacrificar robustez.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, body_n, brake_ratio.
3. Calcular score = body_n * brake_ratio.
4. Filtrar eventos: brake_transition=1 AND score>=X.
5. Evaluar resultado en próxima vela.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, body_n, brake_ratio
- `regla`: brake_transition=1 AND (body_n * brake_ratio)>=X

## Aislamiento

Prueba UNA condición: freno con score combinado de calidad.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp019.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
