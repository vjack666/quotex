# EXP-028 — Consistencia relajada 2/5

## Documentación del Experimento

### Objetivo Principal
Medir si relajar la consistencia a `wins >= 2/5` mejora robustness respecto a EXP-020 (`wins >= 3/5`).

### Hipótesis Formal
H1: Una consistencia más baja aumenta la muestra y puede mejorar robustness sin eliminar demasiada señal.

### Antecedentes y Contexto
EXP-028 surge de EXP-020-027: 3/5 genera señal fuerte pero robustez baja. Aquí se prueba 2/5 como punto de partida más permisivo.

### Diseño Experimental
- **Tipo**: Consistencia relajada sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 y wins>=2/5 en horizontes 1-5
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Evaluar cada evento en velas idx+1 a idx+5
4. Marcar como válido si wins>=2/5
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
Comparar contra EXP-020 para medir el efecto de consistencia relajada.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp028.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
