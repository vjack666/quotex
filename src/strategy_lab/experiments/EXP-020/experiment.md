# EXP-020 — brake_transition con consistencia temporal multi-horizonte

## Documentación del Experimento

### Objetivo Principal
Medir si la señal del freno es consistente en múltiples horizontes temporales (1 a 5 velas), requierendo al menos 3/5 aciertos.

### Hipótesis Formal
H1: Un freno con consistencia multi-horizonte tiene mayor robustez que el freno evaluado en horizonte fijo.

### Antecedentes y Contexto
EXP-020 surge del agotamiento de filtros: todos los filtros sobre `brake_transition` mejoran WR/PF pero no robustez. Aquí se prueba consistencia temporal como criterio alternativo.

### Diseño Experimental
- **Tipo**: Consistencia multi-horizonte sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 y wins>=3 en horizontes 1-5
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Evaluar cada evento en velas idx+1 a idx+5
4. Marcar como válido si wins>=3
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, consistencia temporal
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
Comparar contra EXP-009 (freno puro) y EXP-010-019 para medir el aporte de la consistencia temporal.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp020.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
