# Design — refactor_monolith

## Objetivo

Dividir `src/consolidation_bot.py` (~4170 líneas) en cinco módulos con
responsabilidad única, dejando `consolidation_bot.py` como facade/orquestador
(≤500 líneas) compatible con `main.py` existente.

## Mapa de extracción (origen → destino)

| Bloque actual en `consolidation_bot.py` | Destino | Notas |
|---|---|---|
| `connect_with_retry`, `looks_like_connection_issue` | `connection.py` | Reconexión y clasificación de errores |
| `fetch_candles`, `fetch_candles_with_retry`, `get_open_assets` | `connection.py` | I/O broker |
| `place_order` (+ `_force_reconnect` interno) | `connection.py` | Envío al broker; dry-run incluido |
| `ConsolidationBot.ensure_connection` | `connection.py` | Como método de `ConnectionManager` o función |
| `raw_to_candle` | `connection.py` o `models.py` | Conversión broker → `Candle` |
| `detect_consolidation`, `price_at_*`, `broke_*`, `avg_body`, `is_high_volume_break`, `compute_atr`, `infer_h1_trend`, `find_strong_support_2m` | `strat_a.py` | Lógica pura, sin `Quotex` |
| Integración STRAT-B (`detect_spring_or_upthrust`, adaptación candles→DataFrame) | `strat_b.py` | Reutiliza `strategy_spring_sweep.py` internamente |
| `ConsolidationBot.scan_all` (orquestación, fetch paralelo, recolección candidatos) | `scanner.py` | Llama `connection` + estrategias; no envía órdenes |
| `_enter`, `_resolve_trade`, `_check_martin`, ciclo/martingala, balance/risk, `place_order` vía executor | `executor.py` | Único módulo que dispara órdenes en el pipeline |
| `ConsolidationBot` (estado compartido, `main`, CLI helpers) | `consolidation_bot.py` | Facade que compone scanner + executor |
| Constantes de estrategia (`TF_5M`, `MIN_PAYOUT`, …) | `config.py` (nuevo auxiliar) o reparto por módulo | Necesario para cumplir límite 500 líneas |
| `TradeState`, `PendingReversal`, `MartinPending`, `OrderBlock`, `MAState`, `EntryTimingInfo` | `models.py` (extender) | Evita imports circulares |

## Archivos a crear

### `src/connection.py`

```python
"""WebSocket Quotex: conexión, velas y envío de órdenes."""

async def connect_with_retry(client: Quotex) -> tuple[bool, str]: ...
async def fetch_candles(client: Quotex, asset: str, tf_sec: int, count: int) -> list[Candle]: ...
async def fetch_candles_with_retry(
    client: Quotex, asset: str, tf_sec: int, count: int,
    timeout_sec: float, retries: int = ...,
) -> list[Candle]: ...
async def get_open_assets(client: Quotex, min_payout: int = ...) -> list[tuple[str, int]]: ...
def looks_like_connection_issue(reason: str) -> bool: ...
async def place_order(
    client: Quotex, asset: str, direction: str, amount: float,
    duration: int, dry_run: bool, account_type: str = "PRACTICE",
) -> tuple[bool, str, float, int, str]: ...

class ConnectionManager:
    def __init__(self, client: Quotex): ...
    async def ensure_connection(self) -> bool: ...
```

### `src/strat_a.py`

```python
"""Estrategia A: consolidación en 5m (señal pura)."""

def detect_consolidation(
    candles: list[Candle], max_range_pct: float = ...,
) -> ConsolidationZone | None: ...
def price_at_ceiling(price: float, ceiling: float, tolerance_pct: float = ...) -> bool: ...
def price_at_floor(price: float, floor: float, tolerance_pct: float = ...) -> bool: ...
def broke_above(candle: Candle, ceiling: float) -> bool: ...
def broke_below(candle: Candle, floor: float) -> bool: ...
def is_high_volume_break(candle: Candle, candles_history: list[Candle]) -> bool: ...
def compute_atr(candles: list[Candle], period: int = ...) -> float: ...
def infer_h1_trend(candles_h1: list[Candle]) -> str: ...
def evaluate_strat_a(
    asset: str, candles_5m: list[Candle], candles_1m: list[Candle], zone: ConsolidationZone | None,
) -> CandidateEntry | None: ...
```

`evaluate_strat_a` encapsula la lógica hoy embebida en el loop de `scan_all`
(rebote, ruptura, patrones 1m vía `candle_patterns` / `entry_scorer`).

### `src/strat_b.py`

```python
"""Estrategia B: Spring / Upthrust (Wyckoff) en 1m."""

def candles_to_dataframe(candles: list[Candle]) -> pd.DataFrame: ...
def evaluate_strat_b(candles_1m: list[Candle], min_confidence: float = ...) -> dict | None: ...
```

Delega detección a `strategy_spring_sweep.detect_spring_or_upthrust`.
No elimina `strategy_spring_sweep.py` en esta feature (evita scope creep).

### `src/scanner.py`

```python
"""Descarga de velas y recolección de candidatos por activo."""

@dataclass
class ScanResult:
    candidates: list[CandidateEntry]
    stats_delta: dict[str, int]
    diagnostics: dict[str, Any]

class AssetScanner:
    def __init__(self, connection: ConnectionManager, bot_state: ...): ...
    async def scan_all(self) -> ScanResult: ...
```

Responsabilidades:
- Obtener activos OTC (`get_open_assets`).
- Fetch 5m/1m con semáforo (`CANDLE_FETCH_CONCURRENCY`).
- Invocar `strat_a.evaluate_strat_a` y `strat_b.evaluate_strat_b`.
- Puntuar con `entry_scorer` (`score_candidate`, `select_best`).
- **No** llamar `place_order` directamente.

### `src/executor.py`

```python
"""Ejecución de órdenes, martingala y gestión de ciclo."""

class TradeExecutor:
    def __init__(self, client: Quotex, connection: ConnectionManager, state: ...): ...
    async def enter_trade(self, candidate: CandidateEntry, ...) -> bool: ...
    async def resolve_trade(self, trade: TradeState, asset: str) -> None: ...
    async def refresh_balance_and_risk(self) -> bool: ...
    async def reconcile_pending_candidates(self, max_age_minutes: float | None = ...) -> None: ...
```

Usa `connection.place_order` para envío real/dry-run.
Mantiene integración con `martingale_calculator`, `trade_journal`.

### `src/consolidation_bot.py` (refactorizado, ≤500 líneas)

- Importa y compone `ConnectionManager`, `AssetScanner`, `TradeExecutor`.
- Conserva `class ConsolidationBot` como API estable con métodos delegados:
  `scan_all`, `ensure_connection`, `main`, `log_stats`, etc.
- Conserva `async def main(...)`, `parse_args()`, `sleep_with_inline_countdown`,
  `seconds_until_next_scan`.
- Re-exporta constantes que `main.py` muta en `_apply_runtime_config`.

### `main.py` (raíz)

Cambios mínimos:
```python
import connection
import scanner
import executor
import consolidation_bot as cb
```

`_run` sigue llamando `cb.main(...)`. Los imports explícitos cumplen R7 y
permiten verificar que los módulos son importables.

## Excepciones

Reutilizar las de `docs/conventions.md` (`src/errors.py`, crear si no existe):

| Excepción | Uso |
|---|---|
| `ConnectionError` | Fallo irrecuperable de conexión en `connection.py` |
| `StrategyError` | Entrada inválida en `strat_a` / `strat_b` |
| `RiskError` | Límite de sesión/ciclo en `executor.py` |

El facade captura `BotError` en el loop principal (comportamiento actual).

## Tests planificados (trazabilidad)

| Requirement | Test(s) |
|---|---|
| R1 | `test_consolidation_bot_under_500_lines` |
| R2 | `test_looks_like_connection_issue_*`, `test_fetch_candles_*`, `test_connect_with_retry_*` |
| R3 | `test_scanner_collects_candidates`, `test_scanner_skips_greylisted_asset` |
| R4 | `test_executor_dry_run_order`, `test_executor_cycle_reset_on_target` |
| R5 | `test_detect_consolidation_valid_zone`, `test_broke_above_detects_breakout` |
| R6 | `test_strat_b_spring_signal`, `test_strat_b_no_signal_insufficient_candles` |
| R7 | `test_main_imports_new_modules`, `test_main_once_dry_run_completes` |
| R8 | (archivo `tests/test_connection.py`) |
| R9 | (archivo `tests/test_scanner.py`) |
| R10 | (archivo `tests/test_executor.py`) |
| R11 | Verificación manual/automatizada vía `.\init.ps1` |
| R12 | `test_strat_a_no_side_effects`, `test_strat_b_no_network_imports` |
| R13 | `test_apply_runtime_config_mutates_constants` |
| R14 | `test_consolidation_bot_main_signature_unchanged` |

Datos de test: velas sintéticas en fixtures dentro de cada archivo de test
(o `tests/data/*.json` si el escenario es largo). Mocks de `Quotex` con
`unittest.mock.AsyncMock`.

## Alternativa descartada

**Monolito con subcarpetas (`src/bot/connection.py`, …) sin facade.**

Descartada porque `main.py` y el harness ya importan `consolidation_bot` desde
`src/` en el `sys.path`; mover el entrypoint rompería compatibilidad y exigiría
cambios en `init.ps1`, hub y documentación fuera del alcance de esta feature.

**Reescritura big-bang sin tests intermedios.**

Descartada: el monolito tiene estado compartido complejo (`ConsolidationBot`);
la extracción incremental módulo a módulo con tests verdes tras cada paso reduce
riesgo de regresión.

## Orden de dependencias entre módulos

```
models.py, config.py
    ↑
strat_a.py, strat_b.py  (sin I/O)
    ↑
connection.py           (pyquotex)
    ↑
scanner.py, executor.py
    ↑
consolidation_bot.py    (facade ≤500 líneas)
    ↑
main.py
```

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Imports circulares | Estado en `models.py`; facade solo compone |
| Regresión de comportamiento | Tests con velas grabadas del monolito; smoke `--once` |
| `consolidation_bot.py` >500 líneas | Extraer constantes a `config.py` y dataclasses a `models.py` |