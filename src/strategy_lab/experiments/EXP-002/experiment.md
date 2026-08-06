# EXP-002 — Features derivadas de datos crudos M15 multi-par

## Documentación del Experimento

### Objetivo Principal
Generar eventos desde datos crudos OHLCV M15 de múltiples pares, derivando features de máquina de estados y evaluando si una condición estructural sobrevive al tribunal v1.0.

### Hipótesis Formal
H1: Una condición basada en estructura de velas M15 multi-par (tendencia + rango + volatilidad) genera eventos con WR > 50% y EV > 0, sobreviviendo al tribunal v1.0.

### Antecedentes y Contexto
Primer experimento en probar condiciones genéricas multi-par sin dependencia del dataset pregenerado del Edificio. Busca determinar si hay señales estructurales universales en datos crudos.

### Diseño Experimental
- **Tipo**: Generación de eventos desde datos crudos
- **Población**: 7 pares forex + XAUUSD en M15 desde 2022 a 2026-07
- **Muestra**: 24,461 eventos generados
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares desde parquet
2. Calcular features por par: tendencia (EMA fast/slow), rango (ATR), volatilidad (std returns), cuerpo (body/range)
3. Generar eventos por par según reglas estructurales
4. Unificar eventos multi-par
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: ema_fast, ema_slow, atr, body_ratio, volatility
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR
- **Regla estructural**: EMA fast > EMA slow AND body_ratio > 0.5 AND volatility > percentil_75

### Resultados
- **Eventos totales**: 24,461
- **Win Rate**: 48.87%
- **Expected Value**: -0.0225
- **Profit Factor**: 0.956
- **Power**: 0.0
- **Veredicto**: FAIL (3/7 criterios)

### Análisis de Robustez
- Muestra grande pero sin poder predictivo
- PF < 1.3 umbral mínimo
- Robustez: 1/5 pruebas pasadas
- CI incluye null

### Conclusiones
La condición estructural multi-par NO sobrevive al tribunal v1.0. A pesar de la muestra grande, no genera ventaja estadística. Las condiciones genéricas sin contexto de POI no son promovibles.

### Lecciones Aprendidas
1. Muestra grande no compensa falta de edge real
2. Condiciones genéricas sin contexto POI son insuficientes
3. El tribunal detecta correctamente señales sin poder predictivo
4. Necesario incorporar contexto estructural del Edificio

### Próximos Pasos
Probar condiciones específicas del Edificio: freno en zona POI + martillo M15.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp002.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
