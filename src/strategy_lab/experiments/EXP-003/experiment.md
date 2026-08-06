# EXP-003 — Freno en zona POI + martillo M15 desde datos crudos M15 multi-par

## Documentación del Experimento

### Objetivo Principal
Validar si la condición del Edificio "freno en zona POI + martillo M15" mejora la calidad estadística del sistema de binarias.

### Hipótesis Formal
H1: Los eventos donde ocurre un freno (brake_transition=1) en zona POI (cruce_en_zona=1) y se confirma con martillo M15 (hammer_flag=1) tienen WR > 50% y EV > 0, sobreviviendo al tribunal v1.0.

### Antecedentes y Contexto
EXP-003 es la primera prueba de la condición específica del Edificio en datos multi-par. Surge después que EXP-002 demostró que condiciones genéricas sin contexto POI no son promovibles.

### Diseño Experimental
- **Tipo**: Condición específica del Edificio en datos crudos
- **Población**: 7 pares forex + XAUUSD en M15 desde 2022 a 2026-07
- **Muestra**: 41 eventos generados
- **Periodo**: 4+ años de datos históricos
- **Pares**: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY

### Metodología
1. Cargar datos M15 reales de 7 pares desde parquet
2. Calcular features: brake_mask, cruce_en_zona, hammer_15m
3. Generar eventos: brake_transition=1 AND cruce_en_zona=1 AND hammer_15m=1
4. Evaluar resultado 1v1 (próxima vela cierre vs entrada)
5. Calcular evidencia, robustez y evaluación
6. Exportar informe

### Variables
- **Independientes**: brake_transition, cruce_en_zona, hammer_15m
- **Dependiente**: win/loss por evento
- **Control**: baseline del 37.1% WR
- **Regla Edificio**: brake_transition=1 AND cruce_en_zona=1 AND hammer_15m=1

### Resultados
- **Eventos totales**: 41
- **Win Rate**: 50.00%
- **Expected Value**: 0.0000
- **Profit Factor**: 1.0
- **p-value**: 0.5149
- **Veredicto**: INCONCLUSIVE (0/7 criterios)

### Análisis de Robustez
- Muestra extremadamente chica: 41 eventos
- WR igual a azar: 50%
- No hay poder predictivo demostrable
- PF exactamente 1.0: no hay ventaja

### Conclusiones
La condición "freno en zona POI + martillo M15" NO sobrevive al tribunal v1.0. Aunque la regla parece lógica, en datos históricos genera solo 41 eventos en 4+ años, sin ventaja estadística demostrable.

### Lecciones Aprendidas
1. La condición del Edificio es muy rara en datos históricos
2. Muestra chica invalida cualquier inferencia estadística
3. El martillo M15 como confirmación aislada no genera edge
4. Necesario rediseñar la secuencia o relajar condiciones

### Próximos Pasos
Aumentar ventana de búsqueda del martillo post-freno o replantear la secuencia completa del Edificio.

### Trazabilidad
- **Dataset**: `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\*_M15.parquet`
- **Código**: `src/strategy_lab/scripts/run_experiment_exp003.py`
- **Tribunal**: v1.0
- **Baseline**: BASELINE-EDIFICIO v1.0
- **Fecha**: 2026-08-04
