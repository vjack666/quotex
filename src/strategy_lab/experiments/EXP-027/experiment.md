# EXP-027 — Consistencia 3/5 con alineación de impulso y precio

## Documentación del Experimento

### Objetivo Principal
Medir si exigir que `impulse_net` mantenga el mismo signo en 3/5 horizontes mejora robustness respecto a EXP-020.

### Hipótesis Formal
H1: La consistencia conjunta de precio e impulso reduce falsos positivos y mejora robustness.

### Antecedentes y Contexto
EXP-027 surge de EXP-020-026: la consistencia de precio sola genera señal fuerte pero robustez baja. Aquí se agrega consistencia del impulso como filtro estructural.

### Diseño Experimental
- **Tipo**: Consistencia conjunta precio-impulso
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1, price_wins>=3/5, impulse_consistent>=3/5
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, impulse_net
3. Evaluar cada evento en velas idx+1 a idx+5
4. Marcar como válido si price_wins>=3/5 AND impulse_consistent>=3/5
5. Evaluar resultado en próxima vela
6. Calcular evidencia, robustez y evaluación
7. Exportar informe

### Variables
- **Independientes**: brake_transition, consistencia precio, consistencia impulso
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
Comparar contra EXP-020-026 para medir el efecto de consistencia conjunta.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp027.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
