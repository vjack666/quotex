# EXP-014 — brake_transition (1.5, 1.5) + horizonte 3 velas

## Documentación del Experimento

### Objetivo Principal
Medir si evaluar en vela idx+3 mejora la robustez respecto a horizonte 1 y 2 con el mismo filtro intermedio.

### Hipótesis Formal
H1: Un horizonte de 3 velas aumenta la estabilidad del resultado sin reducir excesivamente los eventos.

### Antecedentes y Contexto
EXP-014 surge de EXP-012 y EXP-013: con horizonte 2 y filtro (1.5, 1.5) se obtuvo WR 57.52% y PF 1.35, pero falló por power/robustness. Aquí se prueba extender el horizonte a 3 velas para dar más tiempo a que la señal se desarrolle.

### Diseño Experimental
- **Tipo**: Variante de horizonte temporal sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5, evaluados en vela idx+3
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, body_n, brake_ratio
3. Filtrar eventos: brake_transition=1 AND body_n>=1.5 AND brake_ratio>=1.5
4. Evaluar resultado en vela idx+3
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
Comparar contra EXP-012 y EXP-013 para medir el efecto del horizonte extendido a 3 velas.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp014.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
