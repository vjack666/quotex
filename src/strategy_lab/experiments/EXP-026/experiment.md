# EXP-026 — Señal pura: dirección del impulso tras brake_transition

## Documentación del Experimento

### Objetivo Principal
Medir si el signo de `impulse_net` en el instante del freno predice la dirección de la próxima vela con WR > baseline.

### Hipótesis Formal
H1: El signo de `impulse_net` en el instante del freno predice la dirección de la próxima vela con WR > baseline.

### Antecedentes y Contexto
EXP-026 surge de EXP-020-025: los filtros de consistencia y estocástico extremo no aportaron robustness. Aquí se prueba la señal más simple posible: dirección por impulso.

### Diseño Experimental
- **Tipo**: Señal direccional pura
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1, dirección por signo de impulse_net
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, impulse_net
3. Fijar dirección: CALL si impulse_net < 0, PUT si impulse_net > 0
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, impulse_net
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
Comparar contra EXP-020-025 para medir el efecto de señal direccional pura.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp026.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
