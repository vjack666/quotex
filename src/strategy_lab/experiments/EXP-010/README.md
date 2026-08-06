# EXP-010 — brake_transition con filtros de calidad del freno

## Objetivo

Robustecer la señal del freno puro (`brake_transition`) agregando filtros de calidad estructural: `body_n_brake` alto y `brake_ratio` alto, sin exigir POI ni martillo.

## Hipótesis

H1: `brake_transition` con `body_n_brake` y `brake_ratio` altos tiene mayor WR, EV y PF que el freno puro, y sobrevive mejor al tribunal v1.0.

## Tribunal

- tribunal.version: 1.0
- baseline.id: BASELINE-EDIFICIO
- baseline.version: 1.0

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, body_n_brake, brake_ratio.
3. Generar eventos: brake_transition=1 AND body_n_brake>umbral AND brake_ratio>umbral.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, body_n_brake, brake_ratio
- `regla`: brake_transition=1 AND body_n_brake>=X AND brake_ratio>=Y

## Aislamiento

Prueba UNA condición: freno con calidad estructural.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp010.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
