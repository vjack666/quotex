# EXP-029 — Consistencia 3/5 con filtro rvol >= 1.5

## Documentación del Experimento

### Objetivo Principal
Medir si agregar `rvol >= 1.5` a la consistencia 3/5 mejora robustness respecto a EXP-020 sin eliminar demasiados eventos.

### Hipótesis Formal
H1: El filtro de volumen relativo reduce eventos de baja convicción y mejora robustness.

### Antecedentes y Contexto
EXP-029 surge de EXP-020-028: la consistencia 3/5 genera señal fuerte pero robustez baja. Aquí se prueba rvol como filtro estructural adicional.

### Diseño Experimental
- **Tipo**: Consistencia + filtro de volumen
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1, wins>=3/5, rvol>=1.5
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, rvol
3. Evaluar consistencia en velas idx+1 a idx+5
4. Marcar como válido si wins>=3/5 AND rvol>=1.5
5. Evaluar resultado en próxima vela
6. Calcular evidencia, robustez y evaluación
7. Exportar informe

### Variables
- **Independientes**: brake_transition, consistencia temporal, rvol
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
Comparar contra EXP-020 para medir el efecto del filtro de volumen.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp029.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
