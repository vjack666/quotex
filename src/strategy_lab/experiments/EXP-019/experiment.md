# EXP-019 — brake_transition con score combinado body_n * brake_ratio

## Documentación del Experimento

### Objetivo Principal
Medir si usar el producto `body_n * brake_ratio` como score único mejora la robustez respecto a umbrales separados.

### Hipótesis Formal
H1: El score combinado captura una interacción no lineal que mejora WR y PF sin sacrificar robustez.

### Antecedentes y Contexto
EXP-019 surge de EXP-010-018: los filtros separados mejoran WR/PF pero no robustez. Aquí se prueba el producto como score único para capturar interacción.

### Diseño Experimental
- **Tipo**: Score combinado sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND (body_n * brake_ratio)>=X
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, body_n, brake_ratio
3. Calcular score = body_n * brake_ratio
4. Filtrar eventos: brake_transition=1 AND score>=X
5. Evaluar resultado en próxima vela
6. Calcular evidencia, robustez y evaluación
7. Exportar informe

### Variables
- **Independientes**: brake_transition, body_n, brake_ratio
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
Comparar contra EXP-010 batch para medir el aporte del score combinado.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp019.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
