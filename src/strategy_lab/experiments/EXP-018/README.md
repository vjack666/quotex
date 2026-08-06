# EXP-018 — Solo rebote post-brake

## Objetivo

Aislar el poder predictivo del rebote después de un brake, sin exigir `brake_transition` ni otros filtros.

## Hipótesis

H1: Los eventos donde ocurre un rebote después de un brake tienen WR significativamente mayor al baseline.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: rebote.
3. Generar eventos: rebote=1.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: rebote
- `regla`: rebote=1

## Aislamiento

Prueba UNA condición: rebote post-brake.
No exige cruce ni martillo ni POI ni brake_transition.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp018.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
