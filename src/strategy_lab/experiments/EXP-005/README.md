# EXP-005 — Solo freno en zona POI (sin cruce ni martillo)

## Objetivo

Aislar el aporte del freno en zona POI sin exigir cruce ni martillo.

## Hipótesis

H1: Los eventos donde ocurre un brake_transition en cruce_en_zona tienen WR > 50% y EV > 0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, cruce_en_zona.
3. Generar eventos: brake_transition=1 AND cruce_en_zona=1.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `regla`: brake_transition=1 AND cruce_en_zona=1

## Aislamiento

Prueba UNA condición: freno en zona POI.
No exige cruce ni martillo.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp005.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
