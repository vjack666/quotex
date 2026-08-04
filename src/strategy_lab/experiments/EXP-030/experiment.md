# EXP-030 — Pipeline secuencial: freno → cruce estocástico → liberación

## Documentación del Experimento

### Objetivo Principal
Medir si la secuencia completa del Edificio — freno, luego cruce estocástico en zona extrema, luego liberación — mejora el win rate respecto a condiciones aisladas.

### Hipótesis Formal
H1: El pipeline secuencial genera eventos de mayor calidad que cualquier condición aislada, porque el cruce actúa como confirmación temporal del freno y la liberación como filtro de entrada.

### Antecedentes y Contexto
EXP-030 surge directamente de la estrategia del Edificio: el usuario insiste en que la entrada no es un filtro paralelo, sino una máquina de estados secuencial. Los experimentos anteriores probaron condiciones aisladas; este prueba la secuencia completa.

### Diseño Experimental
- **Tipo**: Pipeline secuencial de eventos
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos que cumplen brake → cruce en zona extrema → liberación
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, cruce_en_zona, cruce_ago, k, d
3. Buscar secuencia: brake_transition=1 → cruce en zona extrema → liberación
4. La liberación se define como: cruce ocurre, luego cross_ago aumenta y k/d se alejan de zona extrema
5. Evaluar resultado en próxima vela tras liberación
6. Calcular evidencia, robustez y evaluación
7. Exportar informe

### Variables
- **Independientes**: brake_transition, cruce_en_zona, cruce_ago, k, d
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
Comparar contra experimentos de condiciones aisladas para medir el efecto del pipeline secuencial.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp030.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
