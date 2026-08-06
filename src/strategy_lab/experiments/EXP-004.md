# EXP-004 — Pipeline completo Edificio: freno → cruce válido → martillo

## Objetivo

Validar la secuencia completa del Edificio: freno en zona POI → espera → cruce válido del estocástico en zona extrema → martillo de confirmación, midiendo el tiempo de espera como variable principal.

## Hipótesis

H1: Los eventos que cumplen la secuencia completa tienen WR > 50% y EV > 0. Además, existe un umbral óptimo de `minutes_brake_to_cross` donde el WR se maximiza.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_mask, cruce_en_zona, hammer_15m, cross_ago.
3. Generar eventos como máquina de estados:
   - Estado 1: brake_transition=1 y cruce_en_zona=1
   - Estado 2: dentro de 60 min después del freno, aparece cruce válido
   - Estado 3: dentro de 60 min después del cruce, aparece hammer
   - Solo cuando los 3 se cumplen se genera el evento
4. Medir minutes_brake_to_cross, minutes_cross_to_hammer.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, cruce_en_zona, hammer_15m, cross_ago, minutes_brake_to_cross
- `regla_edificio`: brake_transition=1 AND cruce_en_zona=1 AND hammer en ventana post-cruce

## Aislamiento

Prueba UNA secuencia completa del Edificio.
No mezcla con body_n, martillo inmediato, ni otras variables.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp004.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
