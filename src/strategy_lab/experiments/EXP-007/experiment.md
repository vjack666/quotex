# EXP-007 — Solo martillo M15 sin freno ni cruce

## Documentación del Experimento

### Objetivo Principal
Aislar el poder predictivo del martillo M15 sin exigir freno ni cruce.

### Hipótesis Formal
H1: Los eventos donde aparece un martillo M15 tienen WR > 50% y EV > 0.

### Antecedentes y Contexto
EXP-007 es la tercera prueba de descomposición del pipeline del Edificio. Después de demostrar que el freno en POI y el cruce del estocástico no generan edge, se evalúa el tercer componente: el martillo M15 como confirmación.

### Diseño Experimental
- **Tipo**: Condición aislada de patrón de vela
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: 19,993 eventos
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: hammer_15m
3. Generar eventos: hammer_15m=1
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independiente**: hammer_15m=1
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR

### Resultados
- **Eventos totales**: 19,993
- **Win Rate**: 49.21%
- **Expected Value**: -0.0159
- **Profit Factor**: 0.969
- **Power**: 0.0
- **Veredicto**: FAIL (3/7 criterios)

### Análisis de Robustez
- Muestra grande: 19,993 eventos
- WR por debajo de 50%
- EV negativo: -0.0159
- PF < 1.3 umbral mínimo
- Robustez: 1/5 pruebas pasadas

### Conclusiones
El martillo M15 como condición aislada NO genera ventaja estadística. WR 49.21% y EV negativo demuestran que este patrón de vela, sin contexto de freno ni cruce, no es un edge. El martillo necesita el contexto del Edificio para tener valor.

### Lecciones Aprendidas
1. El martillo M15 es un patrón común sin valor predictivo aislado
2. Muestra grande confirma falta de edge
3. El contexto (freno + cruce) es necesario para el martillo
4. El Edificio necesita secuencia completa, no componentes aislados

### Próximos Pasos
Conclusión de la descomposición: ningún componente aislado genera ventaja. Necesario replantear la hipótesis fundamental del Edificio.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp007.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
