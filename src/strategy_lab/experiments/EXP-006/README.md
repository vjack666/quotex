# EXP-006 — Solo cruce del estocástico en zona extrema

## Objetivo

Aislar el poder predictivo del cruce del estocástico en zona extrema sin exigir freno ni martillo.

## Hipótesis

H1: Los eventos donde ocurre un cruce alcista/bajista en zona extrema tienen WR > 50% y EV > 0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: cruce_en_zona.
3. Generar eventos: cruce_en_zona=1.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `regla`: cruce_en_zona=1

## Aislamiento

Prueba UNA condición: cruce en zona extrema.
No exige freno ni martillo.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp006.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
