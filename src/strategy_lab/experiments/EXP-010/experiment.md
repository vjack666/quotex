# EXP-010 — brake_transition con filtros de calidad del freno

## Documentación del Experimento

### Objetivo Principal
Robustecer la señal del freno puro (`brake_transition`) agregando filtros de calidad estructural: `body_n_brake` alto y `brake_ratio` alto, sin exigir POI ni martillo.

### Hipótesis Formal
H1: `brake_transition` con `body_n_brake` y `brake_ratio` altos tiene mayor WR, EV y PF que el freno puro, y sobrevive mejor al tribunal v1.0.

### Antecedentes y Contexto
EXP-010 surge del hallazgo de EXP-009: el freno puro genera WR 54.11% y EV positivo, pero no pasa el tribunal por robustez insuficiente. Aquí se agregan filtros de calidad del freno para aumentar robustez sin perder demasiados eventos.

### Diseño Experimental
- **Tipo**: Filtros de calidad sobre condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1 AND body_n_brake>=X AND brake_ratio>=Y
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, body_n_brake, brake_ratio
3. Generar eventos: brake_transition=1 AND body_n_brake>=X AND brake_ratio>=Y
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, body_n_brake, brake_ratio
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
Comparar contra EXP-009 (freno puro) para medir el aporte de los filtros de calidad.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp010.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
