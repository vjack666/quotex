# EXP-015 — brake_transition alineado con trend de corto plazo

## Documentación del Experimento

### Objetivo Principal
Medir si exigir que el freno ocurra en la dirección del `trend` de corto plazo mejora la robustez respecto al freno puro.

### Hipótesis Formal
H1: `brake_transition` con `trend` alineado tiene mayor WR y PF que el freno puro, porque el contexto direccional filtra falsas rupturas.

### Antecedentes y Contexto
EXP-015 surge de EXP-010-014: los filtros de body_n/brake_ratio/kd_dist mejoran WR/PF pero no robustez. Aquí se prueba `trend` como filtro direccional, más ligado al contexto de mercado.

### Diseño Experimental
- **Tipo**: Filtro direccional sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND trend*impulse_net > 0
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, trend, impulse_net
3. Filtrar eventos: brake_transition=1 AND trend*impulse_net > 0
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, trend, impulse_net
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
Comparar contra EXP-009 (freno puro) y EXP-010-014 para medir el aporte del filtro direccional.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp015.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
