# EXP-024 — Consistencia estricta 3/3 en horizontes 1-3

## Documentación del Experimento

### Objetivo Principal
Medir si exigir 3/3 en horizontes 1-3 mejora robustness respecto a 3/5 en horizontes 1-5.

### Hipótesis Formal
H1: Una ventana más corta y consistencia perfecta reduce la sensibilidad a perturbaciones y mejora robustness.

### Antecedentes y Contexto
EXP-024 surge de EXP-020-023: la consistencia 3/5 genera señales extremas pero robustness baja. Aquí se prueba una ventana más corta con consistencia perfecta.

### Diseño Experimental
- **Tipo**: Consistencia perfecta en ventana corta
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 y wins=3/3 en horizontes 1-3
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Evaluar consistencia en velas idx+1 a idx+3
4. Marcar como válido si wins=3/3
5. Evaluar resultado en próxima vela
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
Comparar contra EXP-020-023 para medir el efecto de ventana corta + consistencia perfecta.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp024.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
