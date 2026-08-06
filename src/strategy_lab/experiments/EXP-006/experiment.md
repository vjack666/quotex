# EXP-006 — Solo cruce del estocástico en zona extrema

## Documentación del Experimento

### Objetivo Principal
Aislar el poder predictivo del cruce del estocástico en zona extrema sin exigir freno ni martillo.

### Hipótesis Formal
H1: Los eventos donde ocurre un cruce alcista/bajista en zona extrema tienen WR > 50% y EV > 0.

### Antecedentes y Contexto
EXP-006 es la segunda prueba de descomposición del pipeline del Edificio. Después de demostrar que el freno en POI no genera edge, se evalúa el segundo componente: el cruce del estocástico en zona extrema.

### Diseño Experimental
- **Tipo**: Condición aislada del estocástico
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: 24,289 eventos
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: cruce_en_zona
3. Generar eventos: cruce_en_zona=1
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independiente**: cruce_en_zona=1
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR

### Resultados
- **Eventos totales**: 24,289
- **Win Rate**: 50.27%
- **Expected Value**: +0.0055
- **Profit Factor**: 1.011
- **Power**: 0.0
- **Veredicto**: INCONCLUSIVE (1/7 criterios)

### Análisis de Robustez
- Muestra muy grande: 24,289 eventos
- WR apenas superior a 50%
- EV positivo pero insignificante: +0.0055
- PF cercano a 1.0: no hay ventaja real
- Robustez: 1/5 pruebas pasadas

### Conclusiones
El cruce del estocástico en zona extrema NO genera ventaja estadística significativa. Aunque la muestra es grande y el WR roza 50%, el EV es casi cero y el PF 1.011. El tribunal lo rechaza por falta de poder predictivo demostrable.

### Lecciones Aprendidas
1. Muestra grande no garantiza edge
2. WR 50.27% con EV +0.0055 es estadísticamente insignificante
3. El cruce en zona extrema es un evento común sin valor predictivo
4. El estocástico como indicador aislado no genera ventaja

### Próximos Pasos
Evaluar componente 3: solo martillo M15 (EXP-007).

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp006.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
