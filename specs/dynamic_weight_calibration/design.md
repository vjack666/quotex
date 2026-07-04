# Design — dynamic_weight_calibration

## Archivo nuevo

`src/weight_calibrator.py` — clase `WeightCalibrator`.

## Archivos modificados

- `src/consolidation_bot.py` — integrar carga de pesos calibrados al inicio.

## Archivo de datos

- `data/exports/calibrated_weights.json` — exportación de pesos calibrados.

## Dependencias

- `trade_journal` — `Journal` para conectar a la BD y leer `candidates`.
- `entry_scorer` — `WEIGHTS_REBOUND`, `WEIGHTS_BREAKOUT` para conocer pesos
  base y poder sobrescribirlos en runtime.
- `models.Candle` — para deserializar `candles_json`.
- `json`, `statistics`, `math`, `pathlib` — stdlib.
- Ninguna dependencia de red (pyquotex, WebSocket).

## Clase WeightCalibrator

### `__init__(self, db_path: Path | None = None)`
- Abre `Journal(db_path)` para acceder a la BD de trades.
- Almacena `self.weights_base` con copias de `WEIGHTS_REBOUND` y
  `WEIGHTS_BREAKOUT`.
- Inicializa `self.trades: list[dict]` vacío.

### `load_trades(self, days: int = 90) -> int`
- Query directa sobre la conexión SQLite:
  ```sql
  SELECT scanned_at, asset, direction, payout, outcome, profit,
         score, score_compression, score_bounce, score_trend, score_payout,
         strategy_origin, candles_json
  FROM candidates
  WHERE outcome IN ('WIN', 'LOSS')
    AND decision = 'ACCEPTED'
    AND scanned_at >= ?
    AND candles_json IS NOT NULL
  ```
- Deserializa `candles_json` → extrae high/low de cada vela.
- Calcula para cada trade:
  - `hour`: hora extraída de `scanned_at`
  - `avg_range`: promedio de `(high - low)` sobre las velas
  - `ratios`: diccionario con `ratio = score_component / weight_base`
    para cada componente (compression, bounce/trend/payout)
  - `adjustments`: `score - (compression + bounce + trend + payout)`
- Retorna la cantidad de trades cargados.

### `_hour_bucket(self, hour: int) -> str`
- Mapea hora a bucket: 0-5 → `"night"`, 6-11 → `"morning"`,
  12-17 → `"afternoon"`, 18-23 → `"evening"`.

### `_determine_vol_regimes(self) -> tuple[float, float]`
- Calcula percentiles 33% y 66% de `avg_range` sobre todos los trades.
- Retorna `(low_threshold, high_threshold)`.

### `_vol_regime(self, avg_range: float, low_th: float, high_th: float) -> str`
- `avg_range <= low_th` → `"low"`
- `low_th < avg_range <= high_th` → `"medium"`
- `avg_range > high_th` → `"high"`

### `_recompute_score(self, trade: dict, weights: dict) -> float`
- `new_base = sum(trade["ratios"][k] * weights[k] for k in weights)`
- `new_total = new_base + trade["adjustments"]`
- Retorna `new_total`.

### `_sharpe(self, profits: list[float]) -> float`
- `mean(p) / stdev(p) * sqrt(n)` con guard para `len < 2` o `stdev = 0`.
- Retorna `-999` si no hay suficientes datos.

### `_optimize_weights(self, trades: list[dict], base_weights: dict) -> dict`
- Genera combinaciones variando cada componente en `[-5, 0, +5]` desde
  el peso base, con paso de 5 y mínimo 5, máximo 60.
- Para cada combinación que sume 100:
  - Recalcula scores con `_recompute_score`
  - Aplica threshold base (65) para filtrar trades "aceptables"
  - Calcula Sharpe de los profits filtrados
- Retorna la combinación con mayor Sharpe (o base si no hay mejora).

### `calibrate(self) -> dict`
- Agrupa `self.trades` por `(hour_bucket, vol_regime)`.
- Para cada grupo con >= 5 trades:
  - Separa por modo (rebound/breakout según `strategy_origin`)
  - Llama a `_optimize_weights` para cada modo.
- Para grupos con < 5 trades, usa los pesos base.
- Retorna diccionario completo de pesos calibrados.

### `export_weights(self, path: Path | None = None) -> Path`
- Si no se especifica path, usa `data/exports/calibrated_weights.json`.
- Serializa el resultado de `calibrate()` a JSON.
- Retorna el path del archivo escrito.

### `load_weights(path: Path) -> dict` (staticmethod)
- Carga y retorna el JSON de pesos calibrados.

### `select_weights(weights_data: dict, hour: int, avg_range: float) -> tuple[dict, dict]`
- Determina bucket horario y régimen de volatilidad.
- Busca en `weights_data["by_group"][mode_key]`.
- Si no encuentra el grupo exacto, usa `default`.
- Retorna `(rebound_weights, breakout_weights)`.

## Integración en startup (consolidation_bot.py)

En la función `main()`, después de crear el bot y antes del loop principal:

```python
# ── Carga de pesos calibrados ──────────────────────────────────────────
try:
    from weight_calibrator import WeightCalibrator
    weights_path = Path(__file__).resolve().parent.parent / "data" / "exports" / "calibrated_weights.json"
    if weights_path.exists():
        weights = WeightCalibrator.load_weights(weights_path)
        # Usar pesos default por ahora — la selección por grupo se hará
        # en un ciclo aparte
        from entry_scorer import WEIGHTS_REBOUND, WEIGHTS_BREAKOUT
        WEIGHTS_REBOUND.update(weights.get("default", {}).get("rebound", {}))
        WEIGHTS_BREAKOUT.update(weights.get("default", {}).get("breakout", {}))
        log.info("✅ Pesos calibrados cargados desde %s", weights_path)
    else:
        log.info("ℹ️ No hay pesos calibrados — usando defaults")
except Exception as exc:
    log.warning("⚠️ No se pudieron cargar pesos calibrados: %s", exc)
```

## Alternativa descartada: optimización evolutiva

Se consideró usar un algoritmo genético para explorar el espacio de pesos
(evolución diferencial con Sharpe como fitness). Se descartó porque:
- El espacio de búsqueda es pequeño (81 combinaciones por grupo).
- Una grid search exhaustiva es más determinista y más fácil de testear.
- Los datos históricos son limitados (centenas, no millones de trades).
- Un AG añadiría complejidad (crossover, mutación, población) sin
  beneficio real sobre grid search.

## Alternativa descartada: determinación de modo por score residual

Se consideró determinar si un trade usó REBOUND o BREAKOUT comparando el
score almacenado con ambas reconstrucciones (la que más se acerque gana).
Se descartó porque `strategy_origin` es suficiente para desambiguar:
- STRAT-MOMENTUM → BREAKOUT
- STRAT-REVERSAL-SWING, STRAT-ORDER-BLOCK → REBOUND
- STRAT-A, STRAT-B → se asume REBOUND por ser la mayoría en datos históricos.
  El modo se sobreescribe en el grupo del JSON, no hay ambigüedad en runtime.

## Fuera de alcance

- Calibración en vivo mientras el bot opera.
- Recalibración automática periódica (se ejecuta como script offline).
- Conexión al broker durante la calibración.
- Pesos por activo individual — solo por grupo (hora + volatilidad).
