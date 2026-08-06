# EXP-022 — Consistencia 3/5 con evaluación alineada en idx+1

## Documentación del Experimento

### Objetivo Principal
Medir si evaluar el resultado en la misma vela que la consistencia (idx+1) mejora robustness respecto a EXP-020 (outcome en idx+2).

### Hipótesis Formal
H1: La alineación entre ventana de consistencia y horizonte de evaluación reduce el desfase temporal y mejora robustness.

### Antecedentes y Contexto
EXP-022 surge de EXP-020/021: la consistencia temporal genera señales muy fuertes pero robustness baja. Aquí se prueba alinear outcome y consistencia en la misma vela.

### Diseño Experimental
- **Tipo**: Consistencia temporal con horizonte alineado
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 y wins>=3 en horizontes 1-5, outcome en idx+1
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Evaluar consistencia en velas idx+1 a idx+5
4. Marcar como válido si wins>=3
5. Evaluar resultado en vela idx+1
6. Calcular evidencia, robustez y evaluación
7. Exportar informe

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
Comparar contra EXP-020 para medir el efecto de alinear outcome y consistencia.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp022.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
