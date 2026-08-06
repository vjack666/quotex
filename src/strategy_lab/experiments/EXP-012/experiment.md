# EXP-012 — brake_transition (1.5, 1.5) + horizonte 2 velas

## Documentación del Experimento

### Objetivo Principal
Medir si la combinación `body_n>=1.5`, `brake_ratio>=1.5` con horizonte de 2 velas mejora la robustez respecto a variantes más estrictas o de horizonte 1.

### Hipótesis Formal
H1: Un filtro intermedio con horizonte extendido aumenta la muestra y la estabilidad sin hundir el WR.

### Antecedentes y Contexto
EXP-012 surge de EXP-010 batch + EXP-011: la variante estricta `(2.0, 2.0)` con horizonte 1 mostró WR 59.34% y PF 1.46, pero solo 1,370 eventos y falló por power/robustness. Aquí se prueba un filtro intermedio con más eventos y horizonte 2 para ver si mejora la estabilidad.

### Diseño Experimental
- **Tipo**: Variante de filtro + horizonte sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5, evaluados en vela idx+2
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, body_n, brake_ratio
3. Filtrar eventos: brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5
4. Evaluar resultado en vela idx+2
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, body_n, brake_ratio, horizonte
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
Comparar contra EXP-010 variante 9 y EXP-011 para medir el efecto combinado de filtro intermedio + horizonte extendido.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp012.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
