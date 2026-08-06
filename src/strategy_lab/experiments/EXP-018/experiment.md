# EXP-018 — Solo rebote post-brake

## Documentación del Experimento

### Objetivo Principal
Aislar el poder predictivo del rebote después de un brake, sin exigir `brake_transition` ni otros filtros.

### Hipótesis Formal
H1: Los eventos donde ocurre un rebote después de un brake tienen WR significativamente mayor al baseline.

### Antecedentes y Contexto
EXP-018 surge del agotamiento de la rama `brake_transition`: todos los filtros probados mejoran WR/PF pero no robustez. Aquí se prueba `rebote` como condición estructural alternativa.

### Diseño Experimental
- **Tipo**: Condición estructural aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con rebote=1
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: rebote
3. Generar eventos: rebote=1
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: rebote
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
Comparar contra EXP-009-017 para medir el aporte del rebote aislado.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp018.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
