# EXP-007 — Solo martillo M15 sin freno ni cruce

## Objetivo

Aislar el poder predictivo del martillo M15 sin exigir freno ni cruce.

## Hipótesis

H1: Los eventos donde aparece un martillo M15 tienen WR > 50% y EV > 0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: hammer_15m.
3. Generar eventos: hammer_15m=1.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `regla`: hammer_15m=1

## Aislamiento

Prueba UNA condición: martillo M15.
No exige freno ni cruce.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp007.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
