# EXP-031 — Clasificación de secuencias: variantes del pipeline P2→P3→entrada

## Documentación del Experimento

### Objetivo Principal
Detectar todas las variantes de la secuencia del Edificio en datos M15 reales y medir el win rate por patrón, para descubrir cuál es la secuencia real y no la asumida teóricamente.

### Hipótesis Formal
H1: No todas las entradas siguen el orden `freno → extremo → cruce → separación → martillo`. Existen variantes con edge propio que el laboratorio debe cuantificar.

### Variantes a detectar
- `freno → extremo → cruce → separación → martillo`
- `cruce → freno` (cruce primero, freno después)
- `freno + cruce casi juntos` (sin martillo)
- `freno + cruce sin separación K/D`
- `extremo se pierde antes de completar`
- `POI roto con rebote fallido`
- `POI roto con rebote exitoso → re-evaluación en POI cercano`
- `freno sin extremo`
- `cruce sin freno previo`
- `martillo sin cruce`

### Diseño Experimental
- **Tipo**: Clasificación de secuencias por variante
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: todos los eventos que coinciden con alguna variante
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, cruce_en_zona, cross_ago, k, d, kd_dist, hammer_15m
3. Detectar todas las variantes de secuencia
4. Evaluar resultado en próxima vela tras evento final
5. Calcular evidencia, robustez y evaluación por variante
6. Exportar informe con ranking de variantes por win rate, PF y robustness

### Variables
- **Independientes**: brake_transition, cruce_en_zona, cross_ago, k, d, kd_dist, hammer_15m
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
Ranking de variantes para definir la secuencia real del mercado.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp031.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
