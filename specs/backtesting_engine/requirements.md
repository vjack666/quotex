# Requirements — backtesting_engine

> Feature id=9. Motor offline que reproduce señales históricas desde
> `trade_journal.db` para validar estrategias sin conexión al broker.
> Cada `R<n>` es verificable por un test concreto.

---

## R1 — Carga de datos históricos

CUANDO el usuario ejecuta el backtester con un rango de días, el sistema
DEBE cargar candidatos de la tabla `candidates` cuya `scanned_at` esté
dentro del rango, incluyendo `candles_json`, `outcome`, `profit`,
`strategy_origin` y `direction`.

## R2 — Re-evaluación con estrategias activas

CUANDO los candidatos históricos están cargados con sus velas
(`candles_json`), el sistema DEBE re-evaluar cada uno invocando la
función de estrategia correspondiente según `strategy_origin` con las
mismas velas, y registrar si la nueva señal coincide con la original.

## R3 — Reporte de rendimiento

CUANDO la re-evaluación completa, el sistema DEBE generar un reporte
textual con: win rate (W / (W + L)), profit neto total, drawdown máximo
(en %) y Sharpe ratio (asumiendo risk-free rate = 0).

## R4 — Sin I/O al broker

MIENTRAS el backtester ejecuta, el sistema NO DEBE realizar llamadas
de red ni enviar órdenes al broker.

## R5 — Comparación de señales

CUANDO se re-evalúa un candidato, el sistema DEBE permitir comparar la
señal histórica (dirección guardada en `direction`) contra la señal
re-evaluada por la estrategia activa, reportando coincidencias y
divergencias.

## R6 — Tests con datos sintéticos

Los tests DEBEN inyectar datos sintéticos en una base de datos en
memoria y verificar que el backtester produce win rate, profit,
drawdown y Sharpe conocidos de antemano.
