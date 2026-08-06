# EXP-029 — Consistencia 3/5 con filtro rvol >= 1.5

## Objetivo

Medir si agregar `rvol >= 1.5` a la consistencia 3/5 mejora robustness respecto a EXP-020 sin eliminar demasiados eventos.

## Hipótesis

H1: El filtro de volumen relativo reduce eventos de baja convicción y mejora robustness.

## Protocolo

1. Cargar datos M15 reales de 7 pares.
2. Calcular features: brake_transition, rvol.
3. Evaluar consistencia en velas idx+1 a idx+5.
4. Marcar evento como válido si:
   - wins>=3/5
   - rvol >= 1.5
5. Evaluar resultado en próxima vela.
6. Calcular evidencia, robustez y evaluación.
7. Exportar informe.

## Variables

- `pares`: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY
- `timeframe`: M15
- `features`: brake_transition, rvol
- `regla`: brake_transition=1 AND wins>=3/5 AND rvol>=1.5

## Aislamiento

Prueba UNA condición: consistencia + volumen relativo.
No exige filtros de calidad, cruce, martillo ni POI.

## Trazabilidad

- Dataset: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- Código: `src/strategy_lab/scripts/run_experiment_exp029.py`
- Tribunal: `src/strategy_lab/config/tribunal_v1.yaml`
