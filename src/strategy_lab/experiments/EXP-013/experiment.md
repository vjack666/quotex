# EXP-013 — brake_transition + kd_dist mínimo

## Documentación del Experimento

### Objetivo Principal
Medir el impacto de agregar un filtro de separación mínima entre K y D en el momento del freno, sin restringir `body_n` ni `brake_ratio`.

### Hipótesis Formal
H1: `brake_transition` con `kd_dist` alto mejora la robustez respecto al freno puro, porque requiere convergencia real del estocástico.

### Antecedentes y Contexto
EXP-013 surge de EXP-010-012: los filtros de `body_n` y `brake_ratio` mejoran WR/PF pero no robustez. Aquí se prueba `kd_dist` como dimensión de calidad alternativa, más ligada al estocástico del Edificio.

### Diseño Experimental
- **Tipo**: Filtro de separación estocástica sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND kd_dist>=X
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, kd_dist
3. Filtrar eventos: brake_transition=1 AND kd_dist>=X
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, kd_dist
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
Comparar contra EXP-009 (freno puro) y EXP-010 batch para medir el aporte de kd_dist.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp013.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
