# EXP-003 — Freno en zona POI + martillo M15 desde datos crudos M15 multi-par

## Objetivo

Validar si la condición del Edificio "freno en zona POI + martillo M15"
mejora la calidad estadística del sistema de binarias.

## Hipótesis

H1: Los eventos donde ocurre un freno (brake_transition=1) en zona POI
(cruce_en_zona=1) y se confirma con martillo M15 (hammer_flag=1)
tienen WR > 50% y EV > 0, sobreviviendo al tribunal v1.0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares desde parquet.
2. Calcular features: brake_mask, cruce_en_zona, hammer_15m.
3. Generar eventos: brake_transition=1 AND cruce_en_zona=1 AND hammer_15m=1.
4. Calcular resultado 1v1 (próxima vela cierre vs entrada).
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, cruce_en_zona, hammer_15m
- `regla_edificio`: brake_transition=1 AND cruce_en_zona=1 AND hammer_15m=1

## Aislamiento

Prueba UNA condición específica del Edificio.
No mezcla con cross_separation, body_n_brake, ni otras variables.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp003.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
