# EXP-008 — Martillo M15 solo dentro de ventana post-cruce

## Documentación del Experimento

### Objetivo Principal
Medir el aporte real del martillo M15 cuando aparece DESPUÉS de un cruce válido del estocástico en zona extrema, sin exigir freno.

### Hipótesis Formal
H1: El martillo M15 post-cruce tiene mayor WR que el martillo aislado, porque incorpora contexto temporal.

### Antecedentes y Contexto
EXP-008 es una prueba intermedia en la descomposición del pipeline del Edificio. Después de demostrar que el martillo aislado no genera edge (EXP-007), se evalúa si el martillo dentro de una ventana post-cruce tiene valor predictivo adicional.

### Diseño Experimental
- **Tipo**: Condición contextualizada
- **Población**: 7 pares forex en M15 desde 2022 a 2026-07
- **Muestra**: eventos con cruce + martillo dentro de 60 min
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares
2. Calcular features: cruce_en_zona, hammer_15m
3. Generar eventos: cruce_en_zona=1 AND hammer_15m=1 dentro de 60 min post-cruce
4. Evaluar resultado en próxima vela
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independiente**: cruce_en_zona=1 AND hammer_15m=1 dentro de 60 min
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR

### Resultados
- **Eventos totales**: 22,972
- **Win Rate**: 49.34%
- **Expected Value**: -0.0131
- **Profit Factor**: 0.974
- **Power**: 0.0
- **Veredicto**: FAIL (3/7 criterios)

### Análisis de Robustez
- Muestra muy grande: 22,972 eventos
- WR por debajo de 50%
- EV negativo: -0.0131
- PF < 1.3 umbral mínimo
- Robustez: 1/5 pruebas pasadas

### Conclusiones
El martillo M15 post-cruce NO genera ventaja estadística. WR 49.34% y EV negativo demuestran que incluso con contexto temporal, el martillo no tiene poder predictivo. Comparado con EXP-007 (martillo aislado: WR 49.21%, EV -0.0159), el contexto temporal NO mejora la señal.

### Lecciones Aprendidas
1. El martillo M15 no tiene valor predictivo ni aislado ni post-cruce
2. El contexto temporal no compensa la falta de edge
3. El patrón de vela es insuficiente como filtro
4. Necesario descartar martillo como componente del Edificio

### Próximos Pasos
Conclusión de la descomposición: martillo no es un componente promovible. Necesario replantear la hipótesis fundamental del Edificio sin depender de patrones de vela aislados.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp008.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
