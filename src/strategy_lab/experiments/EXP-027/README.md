# EXP-027 — Consistencia 3/5 con alineación de impulso y precio

## Objetivo

Medir si exigir que `impulse_net` mantenga el mismo signo en 3/5 horizontes mejora robustness respecto a EXP-020.

## Hipótesis

H1: La consistencia conjunta de precio e impulso reduce falsos positivos y mejora robustness.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, impulse_net.
3. Evaluar cada evento en velas idx+1 a idx+5.
4. Marcar evento como válido si:
   - precio gana en >=3 de 5 horizontes
   - impulse_net mantiene el mismo signo en >=3 de 5 horizontes
5. Evaluar resultado en próxima vela.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, impulse_net
- `regla`: brake_transition=1 AND price_wins>=3/5 AND impulse_consistent>=3/5

## Aislamiento

Prueba UNA condición: consistencia conjunta precio-impulso.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp027.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
