# EXP-008 — Martillo M15 solo dentro de ventana post-cruce

## Objetivo

Medir el aporte real del martillo M15 cuando aparece DESPUÉS de un cruce válido del estocástico en zona extrema, sin exigir freno.

## Hipótesis

H1: El martillo M15 post-cruce tiene mayor WR que el martillo aislado, porque incorpora contexto temporal.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: cruce_en_zona, hammer_15m.
3. Generar eventos: cruce_en_zona=1 Y hammer_15m=1 dentro de 60 min post-cruce.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: cruce_en_zona, hammer_15m
- `regla`: cruce_en_zona=1 AND hammer_15m=1 dentro de 60 min

## Aislamiento

Prueba UNA condición: martillo con contexto temporal post-cruce.
No exige freno.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp008.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
