# Design — backtesting_engine

## Archivo nuevo

`src/backtester.py` — clase `Backtester`.

## Dependencias

- `trade_journal` — `Journal` para conectar a la BD y leer `candidates`.
- `models.Candle` — para deserializar `candles_json`.
- `strat_momentum.detect_momentum_1m`
- `strat_reversal_swing.detect_reversal_swing`
- `strat_order_block.detect_order_block_entry`
- `strat_a.evaluate_strat_a`
- `strat_b.evaluate_strat_b`
- Ninguna dependencia de red (pyquotex, WebSocket).

## Clase Backtester

### `__init__(self, db_path: Path | None = None)`
- Abre `Journal(db_path)` o usa `trade_journal-<fecha>.db` por defecto.

### `load_from_db(self, days: int = 30) -> list[dict]`
- Query: `SELECT * FROM candidates WHERE scanned_at >= ? AND candles_json IS NOT NULL AND strategy_origin IN (...)`
- Deserializa `candles_json` → `list[Candle]`.
- Almacena internamente como `self.candidates: list[BacktestCandidate]`.

### `reevaluate(self, strategies: list[str] | None = None) -> None`
- Itera `self.candidates`.
- Según `strategy_origin` selecciona la función del mapa de estrategias.
- Invoca la función con las velas deserializadas.
- Guarda resultado en `candidate.reevaluated_signal` (direction o None).

#### Mapa de estrategias

| `strategy_origin` en BD | Función | Input |
|---|---|---|
| `STRAT-A` | `evaluate_strat_a(candles_5m=..., candles_1m=..., zone=...)` | `candles_json` + `strategy_json` |
| `STRAT-B` | `evaluate_strat_b(candles_1m)` | `candles_json` |
| `STRAT-MOMENTUM` | `detect_momentum_1m(candles_1m)` | `candles_json` |
| `STRAT-REVERSAL-SWING` | `detect_reversal_swing(candles_1m)` | `candles_json` |
| `STRAT-ORDER-BLOCK` | `detect_order_block_entry(candles_1m)` | `candles_json` |

Para STRAT-A se necesita reconstruir `ConsolidationZone` desde
`strategy_json`. Si algún campo falta, se salta el candidato con log de
advertencia.

### `compare(self) -> dict`
- Por cada candidato: compara `direction` (histórico) vs
  `reevaluated_signal` (nuevo).
- Retorna: `{"total": N, "matches": M, "mismatches": K, "no_signal_now": L}`.

### `report(self) -> str`
- Calcula sobre los candidatos con `outcome IN ('WIN','LOSS')`:
  - **Win rate**: `wins / (wins + losses)`
  - **Profit neto**: suma de `profit`
  - **Drawdown máximo**: peak-to-trough de la curva de profit acumulado
  - **Sharpe ratio**: `mean(returns) / std(returns) * sqrt(periods)` con
    risk-free rate = 0
- Retorna string formateado.

## Cálculo de drawdown

```python
cumulative = list(itertools.accumulate(profits))
peak = max(peak, cumulative[i])
dd = (cumulative[i] - peak) / peak   # expresado como fracción negativa
max_dd = min(max_dd, dd)
```

## Cálculo de Sharpe

```python
returns = [p for p in profits]       # profits individuales como retornos
mean_r = statistics.mean(returns)
std_r  = statistics.stdev(returns) if len(returns) > 1 else 1.0
sharpe = (mean_r / std_r) * sqrt(252 * 1440 / expiry_minutes)
```

Donde `expiry_minutes` es la duración típica de las operaciones (1 minuto
para opciones binarias 1m). Se usa 1440 (minutos por día) para anualizar.

## Alternativa descartada: pandas

Se consideró apoyar el reporte en pandas.DataFrame para facilitar cálculos
vectorizados. Se descartó porque:
- La feature no justifica agregar pandas a las importaciones del backtester;
  el volumen de datos histórico es pequeño (centenas, no millones de trades).
- El bot ya usa `statistics` y `itertools`, que alcanzan.

## Fuera de alcance

- Live trading o conexión al broker.
- Simulación de latencia de red o slippage.
- Reconstrucción de `zone_memory`, `candles_h1`, `candles_15m` — solo se
  usan los datos guardados en la BD.
- Optimización automática de parámetros de estrategias.
