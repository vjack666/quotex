# EXP-030 — Pipeline secuencial: freno → cruce estocástico → liberación

## Objetivo

Medir si la secuencia completa del Edificio — freno, luego cruce estocástico en zona extrema, luego liberación — mejora el win rate respecto a condiciones aisladas.

## Hipótesis

H1: El pipeline secuencial genera eventos de mayor calidad que cualquier condición aislada, porque el cruce actúa como confirmación temporal del freno y la liberación como filtro de entrada.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, cruce_en_zona, cruce_ago.
3. Buscar secuencia: brake_transition=1 → cruce alcista/bajista en zona extrema (k<=20 o k>=80) → liberación del cruce.
4. La liberación se define como: cruce ocurre, luego `cross_ago` aumenta y `k`/`d` se alejan de la zona extrema.
5. Evaluar resultado en próxima vela tras liberación.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, cruce_en_zona, cruce_ago, k, d
- `regla`: brake_transition=1 → cruce en zona extrema → liberación → entry

## Aislamiento

Prueba UNA condición: pipeline secuencial completo.
No exige martillo, POI, cuerpo del freno ni calidad adicional.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp030.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
