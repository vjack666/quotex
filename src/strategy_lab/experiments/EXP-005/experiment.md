# EXP-005 — Solo freno en zona POI (sin cruce ni martillo)

## Documentación del Experimento

### Objetivo Principal
Aislar el aporte del freno en zona POI sin exigir cruce ni martillo.

### Hipótesis Formal
H1: Los eventos donde ocurre un brake_transition en cruce_en_zona tienen WR > 50% y EV > 0.

### Antecedentes y Contexto
EXP-005 es la primera prueba de descomposición del pipeline del Edificio. Surge después que EXP-004 mostró que la secuencia completa no genera ventaja. Aquí se prueba el componente más básico: solo freno en POI.

### Diseño Experimental
- **Tipo**: Condición aislada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: 1,234 eventos
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, cruce_en_zona
3. Generar eventos: brake_transition=1 AND cruce_en_zona=1
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independiente**: brake_transition=1 AND cruce_en_zona=1
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR

### Resultados
- **Eventos totales**: 1,234
- **Win Rate**: 47.33%
- **Expected Value**: -0.0535
- **Profit Factor**: 0.898
- **Power**: 0.0
- **Veredicto**: INCONCLUSIVE (1/7 criterios)

### Análisis de Robustez
- Muestra adecuada: 1,234 eventos
- WR por debajo de 50%
- EV negativo: -0.0535
- PF < 1.3 umbral mínimo
- Robustez: 1/5 pruebas pasadas

### Conclusiones
El freno en zona POI por sí solo NO genera ventaja estadística. WR 47.33% y EV negativo demuestran que esta condición aislada no es un edge. El Edificio necesita componentes adicionales, pero estos no son suficientes por sí solos.

### Lecciones Aprendidas
1. El freno en POI es un evento estructural, pero no predictivo
2. Muestra grande no compensa falta de poder predictivo
3. El componente más básico del Edificio es perdedor neto
4. Necesario evaluar otros componentes para confirmar hipótesis

### Próximos Pasos
Evaluar componente 2: solo cruce del estocástico en zona extrema (EXP-006).

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp005.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
