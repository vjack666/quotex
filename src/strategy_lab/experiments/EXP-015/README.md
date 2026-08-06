# EXP-015 — brake_transition alineado con trend de corto plazo

## Objetivo

Medir si exigir que el freno ocurra en la dirección del `trend` de corto plazo mejora la robustez respecto al freno puro.

## Hipótesis

H1: `brake_transition` con `trend` alineado tiene mayor WR y PF que el freno puro, porque el contexto direccional filtra falsas rupturas.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, trend.
3. Filtrar eventos: brake_transition=1 AND sign(trend) == sign(impulse_net).
4. Evaluar resultado en próxima vela.
5. Calcular evidencia, robustez y evaluación.
6. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, trend, impulse_net
- `regla`: brake_transition=1 AND trend*impulse_net > 0

## Aislamiento

Prueba UNA condición: freno alineado con tendencia.
No exige cruce ni martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp015.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
