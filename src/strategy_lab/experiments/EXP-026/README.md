# EXP-026 — Señal pura: dirección del impulso tras brake_transition

## Objetivo

Medir si el sesgo direccional del impulso tras `brake_transition` genera un edge estadístico sin filtros adicionales.

## Hipótesis

H1: El signo de `impulse_net` en el instante del freno predice la dirección de la próxima vela con WR > baseline.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, impulse_net.
3. Fijar dirección: CALL si impulse_net < 0, PUT si impulse_net > 0.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, impulse_net
- `regla`: brake_transition=1, dirección por signo de impulse_net, outcome en idx+2

## Aislamiento

Prueba UNA condición: freno como señal direccional pura.
No exige filtros de calidad, consistencia, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp026.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
