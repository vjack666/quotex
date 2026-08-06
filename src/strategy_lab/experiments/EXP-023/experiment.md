# EXP-023 — Consistencia 3/5 con evaluación en idx+3

## Documentación del Experimento

### Objetivo Principal
Medir si evaluar el resultado en vela idx+3 mejora robustness respecto a EXP-020 (idx+2) y EXP-022 (idx+1).

### Hipótesis Formal
H1: Un horizonte intermedio reduce el desfase entre señal y outcome sin perder demasiados eventos.

### Antecedentes y Contexto
EXP-023 surge de EXP-020-022: la consistencia 3/5 genera señales fuertes pero robustness baja. Aquí se prueba idx+3 como punto intermedio.

### Diseño Experimental
- **Tipo**: Consistencia temporal con horizonte intermedio
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 y wins>=3 en horizontes 1-5, outcome en idx+3
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Evaluar consistencia en velas idx+1 a idx+5
4. Marcar como válido si wins>=3
5. Evaluar resultado en vela idx+3
6. Calcular evidencia, robustez y evaluación
7. Exportar informe

### Variables
- **Independientes**: brake_transition, consistencia temporal, horizonte de evaluación
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
Comparar contra EXP-020 y EXP-022 para medir el efecto del horizonte intermedio.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp023.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
