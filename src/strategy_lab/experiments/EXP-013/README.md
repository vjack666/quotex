# EXP-013 — brake_transition + kd_dist mínimo

## Objetivo

Medir el impacto de agregar un filtro de separación mínima entre K y D en el momento del freno, sin restringir `body_n` ni `brake_ratio`.

## Hipótesis

H1: `brake_transition` con `kd_dist` alto mejora la robustez respecto al freno puro, porque requiere convergencia real del estocástico.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, kd_dist.
3. Filtrar eventos: brake_transition=1 AND kd_dist>=X.
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, kd_dist
- `regla`: brake_transition=1 AND kd_dist>=X

## Aislamiento

Prueba UNA condición: freno con separación mínima K/D.
No exige cruce ni martillo ni POI ni body_n/brake_ratio.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp013.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
