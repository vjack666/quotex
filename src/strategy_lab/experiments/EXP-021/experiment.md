# EXP-021 — Consistencia temporal endurecida (4/5 horizontes)

## Documentación del Experimento

### Objetivo Principal
Medir si exigir `wins >= 4` en horizontes 1-5 mejora robustness respecto a EXP-020 (`wins >= 3`).

### Hipótesis Formal
H1: Consistencia más estricta reduce falsos positivos y mejora robustness sin sacrificar demasiados eventos.

### Antecedentes y Contexto
EXP-021 surge de EXP-020: la consistencia temporal 3/5 generó una señal muy fuerte (WR 85.31%, PF 5.81) pero robustness 2/5. Aquí se endurece a 4/5 para reducir ruido.

### Diseño Experimental
- **Tipo**: Consistencia temporal endurecida sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 y wins>=4 en horizontes 1-5
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Evaluar cada evento en velas idx+1 a idx+5
4. Marcar como válido si wins>=4
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
Comparar contra EXP-020 para medir el efecto de endurecer la consistencia.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp021.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
