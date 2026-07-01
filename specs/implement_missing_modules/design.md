# Design — implement_missing_modules

## Objetivo

Implementar cuatro módulos ausentes en `src/` para cerrar la feature #2:

| Módulo | Origen | Capa |
|--------|--------|------|
| `smc_analysis.py` | Port desde `QUOTEX\src\smc_analysis.py` | Estrategia (lógica pura) |
| `smc_decision_engine.py` | Port desde `QUOTEX\src\smc_decision_engine.py` | Estrategia (lógica pura) |
| `smc_auto_trader.py` | Nuevo (patrón `smc_dashboard.py` + `connection.py`) | Facade / ejecución |
| `filter_and_sell_otc.py` | Nuevo (patrón `lab/place_demo_sell_fast.py` + `connection.py`) | Facade / ejecución |

`config.py` ya existe desde feature #1 — **no recrear**. Constantes nuevas se
añaden al archivo existente.

---

## Decisión clave: unificar `Candle`

**Elegido:** reutilizar `models.Candle` en lugar de duplicar el dataclass del repo
fuente.

**Motivo:** `connection.py`, `scanner.py` y todas las estrategias ya usan
`models.Candle`. Los módulos SMC deben consumir el mismo tipo para que el trader
pueda pasar velas de `fetch_candles` sin conversión.

**Adaptación del port:** eliminar `Candle` de `smc_analysis.py`; importar
`from models import Candle`. Conservar el resto de enums y dataclasses SMC
(`Bias`, `StructureEventType`, `SwingPoint`, `FVG`, `Zone`, `StructureResult`).

---

## Mapa de archivos

### Crear

| Archivo | Acción |
|---------|--------|
| `src/smc_analysis.py` | Port adaptado (sin `Candle` local) |
| `src/smc_decision_engine.py` | Port adaptado (`from smc_analysis import ...`) |
| `src/smc_auto_trader.py` | Nuevo trader async |
| `src/filter_and_sell_otc.py` | Nuevo bot filtro + venta |
| `tests/test_smc_analysis.py` | Tests unitarios |
| `tests/test_smc_decision_engine.py` | Tests unitarios |
| `tests/test_smc_auto_trader.py` | Tests con mocks |
| `tests/test_filter_and_sell_otc.py` | Tests con mocks |

### Modificar (mínimo)

| Archivo | Cambio |
|---------|--------|
| `src/config.py` | Añadir constantes SMC y filter-sell (ver abajo) |

### Fuera de alcance (esta feature)

- Subcomandos `smc` / `filter-sell` en `main.py` (README los documenta; el
  `main.py` actual solo ejecuta consolidation). Los módulos nuevos exponen
  `async def main(...)` invocable directamente o vía wiring futuro.
- Integración SMC con `entry_scorer` / `executor` del pipeline de consolidación.
- `smc_dashboard.py` (solo referencia de UI; no se porta).

---

## `src/smc_analysis.py`

Port casi literal del fuente QUOTEX con estas adaptaciones:

```python
"""Análisis estructural SMC: swings, BOS/CHoCH, FVG y zonas."""
from __future__ import annotations

from models import Candle  # unificado — no redefinir Candle aquí

# Enums: Bias, StructureEventType
# Dataclasses: SwingPoint, StructureEvent, FVG, Zone, StructureResult

def detect_swings(candles: Sequence[Candle], strength: int = 3) -> list[SwingPoint]: ...
def detect_fvg(candles: Sequence[Candle], min_size_pct: float = 0.0002) -> list[FVG]: ...
def detect_structure(
    candles: Sequence[Candle],
    swing_strength: int = 3,
    min_fvg_pct: float = 0.0002,
) -> StructureResult: ...
```

Regla de negocio invariante (fuente líneas 10, 314–343):

> Zona sin FVG adyacente de polaridad correcta → `score=0` → **excluida** de
> `StructureResult.zones`.

Helpers privados del fuente se conservan: `_label_structure_events`,
`_compute_bias`, `_extract_zones`.

---

## `src/smc_decision_engine.py`

Port literal del fuente con import adaptado:

```python
"""Motor de decisión SMC — Ley de Dictadura HTF."""
from __future__ import annotations

from smc_analysis import (
    Bias,
    StructureEventType,
    StructureResult,
    Zone,
    detect_structure,
)
from models import Candle

class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"

@dataclass
class Decision:
    signal: Signal
    h4_bias: Bias
    m15_bias: Bias
    m1_last_event: StructureEventType | None
    reason: str
    best_zone: Zone | None = None

class SMCDecisionEngine:
    def __init__(
        self,
        h4_candles: Sequence[Candle],
        m15_candles: Sequence[Candle],
        m1_candles: Sequence[Candle],
        h4_strength: int = 3,
        m15_strength: int = 3,
        m1_strength: int = 2,
    ) -> None: ...

    def decide(self) -> Decision: ...
```

Cascada de decisión (5 pasos del fuente):

1. H4 no neutral.
2. M15 alineado con H4.
3. Mejor zona M15 en dirección H4 (oferta si bearish, demanda si bullish).
4. Gatillo M1: último evento debe ser BOS en dirección H4.
5. CHoCH contra H4 → WAIT con etiqueta de trampa.

---

## `src/smc_auto_trader.py`

Trader async que compone `connection` + `SMCDecisionEngine`. Inspirado en
`smc_dashboard.py` (timeframes y fallback H4→H1) pero usando la pila del proyecto.

### Constantes (añadir a `config.py`)

```python
# SMC
TF_M1_SEC = 60
TF_M15_SEC = 900
TF_H1_SEC = 3600
TF_H4_SEC = 14400
SMC_H4_CANDLES = 60
SMC_M15_CANDLES = 80
SMC_M1_CANDLES = 40
SMC_LOOP_INTERVAL_SEC = 60
SMC_DEFAULT_ASSET = "EURUSD_otc"
SMC_MIN_CANDLES_H4 = 10
SMC_MIN_CANDLES_M15 = 10
SMC_MIN_CANDLES_M1 = 6

# Filter sell
FILTER_SELL_DEFAULT_AMOUNT = 1.0
FILTER_SELL_DEFAULT_DURATION = 60
```

### API pública

```python
"""Trader automático SMC multi-timeframe vía connection.py."""
from __future__ import annotations

@dataclass
class SMCTradeResult:
    asset: str
    decision_signal: str
    order_placed: bool
    order_id: str
    reason: str

class SMCAutoTrader:
    def __init__(
        self,
        client: Quotex,
        *,
        asset: str = SMC_DEFAULT_ASSET,
        amount: float = MIN_ORDER_AMOUNT,
        duration: int = TF_M1_SEC,
        dry_run: bool = True,
        account_type: str = "PRACTICE",
    ) -> None: ...

    async def run_once(self) -> SMCTradeResult: ...
    async def run_loop(self, interval_sec: int = SMC_LOOP_INTERVAL_SEC) -> None: ...

async def main(
    *,
    asset: str = SMC_DEFAULT_ASSET,
    amount: float = MIN_ORDER_AMOUNT,
    duration: int = TF_M1_SEC,
    dry_run: bool = True,
    loop: bool = False,
    real_account: bool = False,
) -> None: ...
```

### Flujo `run_once`

```
ConnectionManager.ensure_connection()
    → fetch H4 (o H1 fallback) / M15 / M1 vía fetch_candles_with_retry
    → validar mínimos SMC_MIN_CANDLES_*
    → SMCDecisionEngine(h4, m15, m1).decide()
    → si BUY/SELL: place_order(direction="call"|"put")
    → si WAIT: log reason, order_placed=False
    → devolver SMCTradeResult
```

Mapeo señal → dirección broker (convención pyquotex del proyecto):

| `Signal` | `direction` en `place_order` |
|----------|------------------------------|
| `BUY` | `"call"` |
| `SELL` | `"put"` |

Logging: módulo `logging.getLogger("smc_auto_trader")`, nivel INFO para señales y
órdenes, DEBUG para datos insuficientes.

---

## `src/filter_and_sell_otc.py`

Bot de filtro por payout y venta en el activo OTC de mayor payout. Inspirado en
`lab/place_demo_sell_fast.py` pero con `connection.get_open_assets` y
`connection.place_order`.

### API pública

```python
"""Escaneo OTC por payout mínimo y venta (PUT) en el mejor candidato."""
from __future__ import annotations

@dataclass
class FilterSellResult:
    asset: str
    payout: int
    order_placed: bool
    order_id: str
    reason: str

class FilterSellBot:
    def __init__(
        self,
        client: Quotex,
        *,
        min_payout: int = MIN_PAYOUT,
        amount: float = FILTER_SELL_DEFAULT_AMOUNT,
        duration: int = FILTER_SELL_DEFAULT_DURATION,
        dry_run: bool = True,
        account_type: str = "PRACTICE",
    ) -> None: ...

    async def run_once(self) -> FilterSellResult: ...
    async def run_loop(self, interval_sec: int = SCAN_INTERVAL_SEC) -> None: ...

async def main(
    *,
    min_payout: int = MIN_PAYOUT,
    amount: float = FILTER_SELL_DEFAULT_AMOUNT,
    duration: int = FILTER_SELL_DEFAULT_DURATION,
    dry_run: bool = True,
    loop: bool = False,
    real_account: bool = False,
) -> None: ...
```

### Flujo `run_once`

```
ConnectionManager.ensure_connection()
    → assets = get_open_assets(client, min_payout)
    → si vacío: FilterSellResult(order_placed=False, reason="sin candidatos")
    → elegir assets[0] (ya ordenado por payout desc en connection.py)
    → place_order(asset, direction="put", amount, duration, dry_run)
    → FilterSellResult con payout y order_id
```

**Nota:** `get_open_assets` ya filtra `sym.endswith("_otc")`, `is_open` y
`payout >= min_payout`, ordenado por payout descendente — reutilizar sin duplicar.

---

## Excepciones

Reutilizar `errors.py` existente:

| Excepción | Uso |
|-----------|-----|
| `ConnectionError` | Fallo irrecuperable de conexión en traders |
| `StrategyError` | Datos de velas inválidos para análisis SMC |

Los traders capturan excepciones en el loop, las registran y continúan (no propagar
stack trace al log como error no manejado).

---

## Tests planificados (trazabilidad)

| Requirement | Test(s) |
|-------------|---------|
| R1 | `test_detect_swings_finds_high_and_low` |
| R2 | `test_detect_fvg_bullish_gap`, `test_detect_fvg_bearish_gap` |
| R3 | `test_detect_structure_returns_full_result` |
| R4 | `test_zones_without_adjacent_fvg_excluded` |
| R5 | `test_detect_structure_insufficient_candles_returns_neutral` |
| R6 | `test_smc_analysis_no_pyquotex_import` |
| R7 | `test_smc_decision_engine_instantiates` |
| R8 | `test_decide_wait_when_h4_neutral` |
| R9 | `test_decide_wait_when_m15_conflicts_h4` |
| R10 | `test_decide_buy_full_cascade` |
| R11 | `test_decide_sell_full_cascade` |
| R12 | `test_decide_wait_on_m1_choch_trap` |
| R13 | `test_smc_decision_engine_no_pyquotex_import` |
| R14 | `test_smc_auto_trader_run_once_completes_cycle` |
| R15 | `test_smc_auto_trader_places_order_on_sell_signal` |
| R16 | `test_smc_auto_trader_skips_order_on_wait` |
| R17 | `test_smc_auto_trader_h4_fallback_to_h1` |
| R18 | `test_smc_auto_trader_dry_run_no_real_buy` |
| R19 | `test_filter_sell_scans_open_assets` |
| R20 | `test_filter_sell_places_put_on_highest_payout` |
| R21 | `test_filter_sell_no_candidates_skips_order` |
| R22 | `test_filter_sell_dry_run` |
| R23 | (archivo `tests/test_smc_analysis.py`) |
| R24 | (archivo `tests/test_smc_decision_engine.py`) |
| R25 | (archivos `tests/test_smc_auto_trader.py`, `tests/test_filter_and_sell_otc.py`) |
| R26 | Verificación vía `.\init.ps1` |
| R27 | Revisión manual: `config.py` no duplicado |

### Fixtures de velas sintéticas

Los tests de decisión construirán secuencias mínimas que produzcan:

- Swings alternados con HH/HL o LH/LL según escenario.
- FVG adyacente a swing para que la zona sea válida.
- Último evento M1 controlado (BOS_UP, BOS_DOWN, CHOCH_UP, CHOCH_DOWN).

Patrón de mock (consistente con `tests/conftest.py`):

```python
@pytest.fixture
def mock_quotex():
    client = AsyncMock()
    client.connect = AsyncMock(return_value=(True, ""))
    ...
```

---

## Alternativas descartadas

**Duplicar `Candle` en `smc_analysis.py` como en el repo fuente.**

Descartada: obligaría conversión en cada ciclo del trader y rompe homogeneidad con
`models.py` exigida en `docs/conventions.md`.

**Integrar SMC en `scanner.py` / `executor.py` en esta feature.**

Descartada: scope creep; la feature #2 solo exige existencia de módulos y tests.
La integración al pipeline de consolidación es trabajo futuro.

**Usar `AsyncQuotexClient` (api_quotex) como en `smc_dashboard.py` y lab/.**

Descartada: el proyecto refactorizado (#1) estandarizó `pyquotex.stable_api.Quotex`
+ `connection.py`. Los traders nuevos deben usar esa capa.

**Recrear `config.py` desde cero.**

Descartada explícitamente en feature_list.json y R27.

---

## Orden de dependencias

```
models.py, config.py (existentes)
    ↑
smc_analysis.py          (puro)
    ↑
smc_decision_engine.py   (puro)
    ↑
connection.py            (I/O)
    ↑
smc_auto_trader.py, filter_and_sell_otc.py
    ↑
tests/test_*.py
```

---

## Riesgos y mitigación

| Riesgo | Mitigación |
|--------|------------|
| Broker no ofrece velas H4 | Fallback H1 con 4× conteo (patrón `smc_dashboard.py`) |
| Tests de decisión frágiles con velas sintéticas | Fixtures documentadas por escenario; asserts sobre `signal` y `reason` |
| Divergencia port vs fuente QUOTEX | Diff manual contra fuente; solo cambiar import `Candle` |
| `main.py` sin subcomandos SMC | Módulos invocables vía `python -m` o `asyncio.run(main())`; README actualización fuera de scope |