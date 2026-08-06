# EXP-001 — Filtro cross_separation y minutes_brake_to_cross

## Documentación del Experimento

### Objetivo Principal
Validar si combinar separación amplia entre líneas K/D del estocástico con un tiempo mínimo desde freno hasta cruce mejora la calidad estadística del Edificio.

### Hipótesis Formal
H1: Las entradas con `cross_separation >= 4.5` y `minutes_brake_to_cross >= 16` tienen win rate significativamente mayor al 50% y valor esperado positivo, sobreviviendo al tribunal v1.0.

### Antecedentes y Contexto
El Edificio actualmente usa `cross_separation > 5` como filtro, pero con solo 61 eventos (WR 59.02%, PF 1.44). Se exploró relajar el umbral a `>=4.5` para aumentar muestra sin perder calidad.

### Diseño Experimental
- **Tipo**: Filtro estadístico sobre eventos históricos
- **Población**: 946 eventos reales del Edificio
- **Muestra**: 126 eventos con cross_separation >=4.5 y minutes_brake_to_cross >=16
- **Periodo**: Datos históricos disponibles del Edificio
- **Pares evaluados**: Según dataset base

### Metodología
1. Cargar dataset real del Edificio (946 eventos)
2. Filtrar por condiciones combinadas
3. Calcular métricas de evidencia
4. Ejecutar pruebas de robustez
5. Evaluar con promotion_gate.py

### Variables
- Independiente: cross_separation >=4.5, minutes_brake_to_cross >=16
- Dependiente: win/loss por evento
- Control: baseline del 37.1% WR

### Resultados
- **Eventos totales**: 126
- **Win Rate**: 47.62%
- **Expected Value**: -0.0476
- **Profit Factor**: 0.91
- **p-value**: 0.0164
- **Veredicto**: INCONCLUSIVE (0/7 criterios)

### Análisis de Robustez
- Divergencia train/test: alta
- Muestra insuficiente para significancia estadística
- PF < 1.3 umbral mínimo
- No pasa criterios de robustez del tribunal

### Conclusiones
La condición `cross_separation >=4.5` y `minutes_brake_to_cross >=16` NO sobrevive al tribunal v1.0. Aunque muestra WR superior al baseline en trainset, no generaliza a testset y no genera profit factor suficiente.

### Lecciones Aprendidas
1. Relajar umbrales no necesariamente aumenta muestra útil
2. El filtro combinado genera sobreajuste
3. El tribunal es efectivo detectando señales espurias
4. Se requiere enfoque diferente, no ajuste de parámetros

### Próximos Pasos
Replantear la hipótesis: probar condiciones estructurales multi-par en lugar de ajustar filtros existentes.

### Trazabilidad
- **Dataset**: `src/strategy_lab/results/edificio_events.csv`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp001.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
