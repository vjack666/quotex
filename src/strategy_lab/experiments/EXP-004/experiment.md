# EXP-004 — Pipeline completo Edificio: freno → cruce válido → martillo

## Documentación del Experimento

### Objetivo Principal
Validar la secuencia completa del Edificio: freno en zona POI → espera → cruce válido del estocástico en zona extrema → martillo de confirmación, midiendo el tiempo de espera como variable principal.

### Hipótesis Formal
H1: Los eventos que cumplen la secuencia completa tienen WR > 50% y EV > 0. Además, existe un umbral óptimo de `minutes_brake_to_cross` donde el WR se maximiza.

### Antecedentes y Contexto
EXP-004 es la prueba más ambiciosa: replicar la secuencia exacta del Edificio según documentación. Surge después que EXP-003 mostró que condiciones aisladas no son suficientes. Aquí se prueba la máquina de estados completa.

### Diseño Experimental
- **Tipo**: Pipeline secuencial completo del Edificio
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: 1,155 eventos que cumplen toda la secuencia
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition, cruce_en_zona, hammer_15m, cross_ago
3. Generar eventos como máquina de estados:
   - Estado 1: brake_transition=1 y cruce_en_zona=1
   - Estado 2: dentro de 60 min después del freno, aparece cruce válido
   - Estado 3: dentro de 60 min después del cruce, aparece hammer
   - Solo cuando los 3 se cumplen se genera el evento
4. Medir minutes_brake_to_cross, minutes_cross_to_hammer
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, cruce_en_zona, hammer_15m, cross_ago
- **Dependientes**: win/loss, minutes_brake_to_cross, minutes_cross_to_hammer
- **Control**: baseline del 37.1% WR
- **Regla Edificio**: brake_transition=1 AND cruce_en_zona=1 AND hammer en ventana post-cruce

### Resultados
- **Eventos totales**: 1,155
- **Train/Test**: 577/578
- **Win Rate**: 47.79%
- **Expected Value**: -0.0442
- **Profit Factor**: 0.915
- **Power**: 0.0
- **Veredicto**: INCONCLUSIVE (1/7 criterios)

### Análisis de Robustez
- Muestra adecuada: 1,155 eventos
- WR por debajo de 50%
- EV negativo: -0.0442
- PF < 1.3 umbral mínimo
- Robustez: 1/5 pruebas pasadas
- Power 0.0: no hay poder predictivo demostrable

### Conclusiones
La secuencia completa del Edificio NO sobrevive al tribunal v1.0. A pesar de tener muestra suficiente (1,155 eventos), el WR es 47.79% y EV negativo. Esto demuestra que la secuencia completa, tal como está documentada, no genera ventaja estadística en datos históricos.

### Lecciones Aprendidas
1. La secuencia completa del Edificio no genera edge
2. Muestra suficiente no compensa regla perdedora
3. El tiempo de espera no determina el resultado
4. Necesario replantear la hipótesis fundamental

### Próximos Pasos
Descomponer la secuencia para aislar componentes fallidos: EXP-005 (solo freno), EXP-006 (solo cruce), EXP-007 (solo martillo).

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp004.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
