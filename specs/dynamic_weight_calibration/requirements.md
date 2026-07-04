# Requirements — dynamic_weight_calibration

> Feature id=10. Sistema que ajusta dinámicamente los pesos del
> `entry_scorer` según condiciones de mercado (volatilidad, hora, sesión,
> rendimiento reciente). Cada `R<n>` es verificable por un test concreto.

---

## R1 — Carga de historial de trades

CUANDO el `WeightCalibrator` se instancia con una ruta de base de datos
válida, el sistema DEBE cargar candidatos de la tabla `candidates` cuyo
`outcome` sea `WIN` o `LOSS` y que tengan `decision='ACCEPTED'`, incluyendo
`scanned_at`, `score_compression`, `score_bounce`, `score_trend`,
`score_payout`, `profit`, `strategy_origin` y `candles_json`.

## R2 — Cálculo de pesos óptimos por grupo

CUANDO los trades históricos están cargados, el sistema DEBE agruparlos
por bucket horario (0-5, 6-11, 12-17, 18-23) y régimen de volatilidad
(bajo/medio/alto según percentiles del rango promedio de velas), y para
cada grupo DEBE evaluar combinaciones de pesos candidatas seleccionando
la que maximice el Sharpe ratio sobre los trades del grupo.

## R3 — Exportación a JSON

CUANDO la calibración completa, el sistema DEBE exportar los pesos
calibrados a un archivo JSON con la estructura: `calibrated_at`,
`total_trades_used`, `by_group` con los grupos horario/volatilidad y
sus pesos óptimos para `rebound` y `breakout`, y un grupo `default`
con los pesos base.

## R4 — Carga de pesos al inicio del bot

CUANDO el bot inicia, el sistema DEBE intentar cargar el archivo JSON
de pesos calibrados desde `data/exports/calibrated_weights.json`. SI el
archivo existe, el sistema DEBE sobrescribir `entry_scorer.WEIGHTS_REBOUND`
y `entry_scorer.WEIGHTS_BREAKOUT` con los pesos correspondientes al grupo
determinado por la hora actual y la volatilidad del mercado. SI el archivo
no existe, el sistema DEBE continuar con los pesos por defecto.

## R5 — Tests con datos sintéticos

Los tests DEBEN inyectar datos sintéticos en una base de datos SQLite en
memoria y verificar que el `WeightCalibrator` produce un archivo JSON con
la estructura esperada, que los pesos cargados coinciden con los exportados
y que la calibración no falla con datos mínimos (menos de 5 trades).

## R6 — Determinación de volatilidad desde velas

CUANDO se carga un trade con `candles_json`, el sistema DEBE calcular el
rango promedio (high-low) de las velas como proxy de volatilidad. Los
regímenes se determinan por percentiles: bajo ≤ 33%, medio > 33% y ≤ 66%,
alto > 66% sobre todos los trades cargados.
