# EXP-017 — brake_transition con rvol>=1.5 + horizonte 4 velas

## Documentación del Experimento

### Objetivo Principal
Medir si combinar `rvol>=1.5` con un horizonte de 4 velas mejora la robustez del freno puro.

### Hipótesis Formal
H1: `brake_transition` con `rvol>=1.5` evaluado en vela idx+4 tiene mayor WR y PF que variantes más cortas, porque da tiempo a que el brake se desarrolle.

### Antecedentes y Contexto
EXP-017 surge de EXP-010-016: los filtros mejoran WR/PF pero no robustez. Aquí se prueba la combinación de `rvol>=1.5` con horizonte extendido para ver si más tiempo ayuda.

### Diseño Experimental
- **Tipo**: Combinación filtro + horizonte sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND rvol>=1.5, evaluados en vela idx+4
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, rvol
3. Filtrar eventos: brake_transition=1 AND rvol>=1.5
4. Evaluar resultado en vela idx+4
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, rvol, horizonte
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
Comparar contra EXP-016 para medir el efecto combinado de rvol + horizonte extendido.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp017.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
