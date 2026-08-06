# EXP-009 — Solo brake_transition=1 (sin cruce_en_zona)

## Objetivo

Aislar el aporte del freno como evento estructural, sin exigir que ocurra en zona POI.

## Hipótesis

H1: Los eventos donde ocurre un brake_transition tienen WR > 50% y EV > 0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition.
3. Generar eventos: brake_transition=1.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `regla`: brake_transition=1

## Aislamiento

Prueba UNA condición: freno sin zona POI.
No exige cruce ni martillo.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp009.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
