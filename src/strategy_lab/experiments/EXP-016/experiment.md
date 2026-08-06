# EXP-016 — brake_transition con filtro de volumen relativo alto

## Documentación del Experimento

### Objetivo Principal
Medir si exigir `rvol` alto en el momento del freno mejora la robustez del freno puro.

### Hipótesis Formal
H1: `brake_transition` con `rvol` alto tiene mayor WR y PF que el freno puro, porque un brake con volumen elevado es más confiable.

### Antecedentes y Contexto
EXP-016 surge de EXP-010-015: los filtros de body_n/brake_ratio/kd_dist/trend no pasaron robustness. Aquí se prueba `rvol` como dimensión de calidad alternativa, ligada a convicción del mercado.

### Diseño Experimental
- **Tipo**: Filtro de volumen relativo sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND rvol>=X
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, rvol
3. Filtrar eventos: brake_transition=1 AND rvol>=X
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, rvol
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR

### Resultados
- Pendientes de ejecución

### Análisis de Robustez
- Pendiente

### Conclusiones
- Pendiente

### Lecciones Aprendidas
- Pendiente

### Próximos Pasos
Comparar contra EXP-009 (freno puro) y EXP-010-015 para medir el aporte de rvol.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp016.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
