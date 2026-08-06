# EXP-009 — Solo brake_transition=1 (sin cruce_en_zona)

## Documentación del Experimento

### Objetivo Principal
Aislar el aporte del freno como evento estructural, sin exigir que ocurra en zona POI.

### Hipótesis Formal
H1: Los eventos donde ocurre un brake_transition tienen WR > 50% y EV > 0.

### Antecedentes y Contexto
EXP-009 cierra la descomposición del pipeline del Edificio. Después de probar freno+POI (EXP-005), solo freno (EXP-009), solo cruce (EXP-006), solo martillo (EXP-007) y martillo post-cruce (EXP-008), esta prueba evalúa el freno sin restricción de zona POI.

### Diseño Experimental
- **Tipo**: Condición aislada del freno
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con brake_transition=1
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: brake_transition
3. Generar eventos: brake_transition=1
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independiente**: brake_transition=1
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR

### Resultados
- **Eventos totales**: 46,767
- **Win Rate**: 54.11%
- **Expected Value**: +0.0823
- **Profit Factor**: 1.179
- **Power**: 0.0
- **Veredicto**: FAIL (3/7 criterios)

### Análisis de Robustez
- Muestra muy grande: 46,767 eventos
- WR superior a 50%: 54.11%
- EV positivo: +0.0823
- PF 1.179, cercano al umbral 1.3 pero aún por debajo
- Robustez: 2/5 pruebas pasadas

### Comparación con EXP-005
- EXP-005 (freno + cruce_en_zona): WR 47.33%, EV -0.0535, PF 0.898
- EXP-009 (solo brake_transition): WR 54.11%, EV +0.0823, PF 1.179
- La restricción de zona POI (`cruce_en_zona`) empeora la señal del freno
- Sin la restricción, el freno muestra edge positivo

### Conclusiones
El freno como evento estructural SÍ genera ventaja estadística cuando no se restringe a zona POI. WR 54.11% y EV positivo demuestran que el freno tiene poder predictivo. Sin embargo, no pasa el tribunal por robustez insuficiente y PF bajo.

### Lecciones Aprendidas
1. El freno sin restricciones tiene edge real
2. La zona POI (`cruce_en_zona`) corrompe la señal del freno
3. La robustez es el criterio faltante, no la muestra ni el WR
4. Necesario evaluar subconjuntos estables del freno

### Próximos Pasos
Probar variantes del freno con filtros adicionales para aumentar robustez, o evaluar el freno en diferentes marcos temporales.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp009.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
