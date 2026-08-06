# EXP-011 — brake_transition alta calidad + horizonte 2 velas

## Documentación del Experimento

### Objetivo Principal
Medir el impacto de ampliar el horizonte de evaluación a 2 velas después del freno, manteniendo los filtros de calidad `body_n` y `brake_ratio` altos.

### Hipótesis Formal
H1: Extender el horizonte a 2 velas aumenta la robustez de la señal del freno puro sin reducir excesivamente los eventos.

### Antecedentes y Contexto
EXP-011 surge de EXP-010 batch: la variante `(2.0, 2.0)` mostró WR 59.34% y PF 1.46, pero solo 1,370 eventos y falló por power/robustness. Aquí se prueba el mismo filtro estricto evaluando 2 velas adelante para ver si mejora la estabilidad sin matar la muestra.

### Diseño Experimental
- **Tipo**: Variante de horizonte temporal sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND body_n>=2.0 AND brake_ratio>=2.0, evaluados en vela idx+2
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, body_n, brake_ratio
3. Filtrar eventos: brake_transition=1 AND body_n>=2.0 AND brake_ratio>=2.0
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
Comparar contra EXP-010 variante 10 para medir el efecto del horizonte extendido.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp011.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
