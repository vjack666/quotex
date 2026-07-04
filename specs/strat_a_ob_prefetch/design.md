# Design — strat_a_ob_prefetch

> Feature id=21. Fase SA-5 — eliminar latencia OB en hot path STRAT-A.
> Referencias: `docs/ROADMAP_STRAT_A.md` (SA-5), `progress/prep_strat_a_ob_prefetch.md`,
> `src/scan_prefetch.py`, `src/scanner.py`, `src/candle_cache.py`,
> `src/parallel_fetch.py`, `src/strat_a.py`, `progress/impl_scan_orchestration.md`.
> Depende de #20 (`strat_a_htf_zone_wiring`).

---

## Objetivo

**No es greenfield.** La orquestación #3 ya prefetcha OB 3m en fase 3b y evaluate no
hace `await fetch_candles` OB. #21 **cierra gaps** respecto a acceptance:

| Componente | Estado actual (2026-07) | Objetivo (#21) |
|------------|-------------------------|----------------|
| Fetch OB en evaluate | ✅ Ninguno (prefetch 3b) | Confirmado + test R18 |
| `detect_order_blocks` | ❌ En bucle evaluate (~L1280) | ✅ En prefetch |
| `ScanCycleData.blocks_by_symbol` | ❌ No existe | ✅ Poblado en 3b |
| `_fetch_ob_candles` | ❌ Dead code (~L297) | ✅ Eliminado |
| Tests blocks → evaluate | ❌ | ✅ Spy R19 |
| `parallel_fetch.py` | Sin uso en prefetch | Opcional DRY (P2) |

**Criterio rendimiento (ROADMAP SA-5):** tiempo de scan por ciclo no crece
linealmente con N activos por I/O OB — verificado por R13/R18 y log
`scan_fetch_elapsed_ms`.

**Fuera de alcance (#21):** HTF 15m / zone_memory (#20), cambiar algoritmo
`detect_order_blocks`, prefetch H1 (permanece en 3b), radar tick OB dedicado,
validación demo (#22).

---

## Decisión de arquitectura: fase 3b + blocks precalculados

El prep recomienda **no fusionar** OB en el `gather` primario 5m+1m salvo presión
extrema de latencia:

| Opción | Pros | Contras | Decisión |
|--------|------|---------|----------|
| Un solo gather 5m+1m+OB todos los symbols | Literal "con 5m/1m" | +N fetches OB inútiles para activos sin STRAT-A | ❌ Descartada |
| Fase 3b + `blocks_by_symbol` (actual + extensión) | Mínimo diff; subconjunto `strat_a_symbols`; paralelo con semáforo | OB no en mismo `gather` que 5m/1m | ✅ **Elegida** |
| Refactor `parallel_fetch.fetch_candles_parallel` | DRY semáforo | No bloquea cierre #21 | P2 opcional |

**Interpretación de acceptance** *"prefetchan en paralelo con 5m/1m"* (R1): mismo
stack (`asyncio.gather`, `CANDLE_FETCH_CONCURRENCY`, `candle_cache`), toda I/O de
velas completa antes de evaluate; OB en gather paralelo dedicado 3b, no secuencial
por activo en hot path.

---

## Arquitectura objetivo

```
scan_all()
  FASE 1  _scan_phase_prepare()
  FASE 2  prefetch_primary_candles()          → 5m + 1m (gather único)
  FASE 3b prefetch_strat_a_secondary()        → OB 3m + H1 (strat_a_symbols)
            ├─ asyncio.gather + semáforo + candle_cache
            ├─ _resolve_ob_candles → candles_ob, ob_tf_labels
            └─ blocks_by_symbol[sym] = detect_order_blocks(candles_ob[sym])  # NUEVO
  FASE 3  _scan_phase_evaluate_assets(cycle)
            └─ blocks = cycle.blocks_by_symbol[sym]   # sin detect_order_blocks
               evaluate_strat_a(..., blocks=blocks)
            └─ assert: 0 network I/O tf=180 en esta fase
  FASE 4/5 selección + ejecución
```

**Coordinación con #20:** OB usa `bot.candle_cache` y `CANDLE_FETCH_CONCURRENCY`;
HTF 15m usa `HTFScanner` con cache propio — semáforos independientes, sin
competencia directa en hot path evaluate.

---

## Archivos a modificar

| Archivo | Cambio | Prioridad |
|---------|--------|-----------|
| `src/scan_prefetch.py` | `ScanCycleData.blocks_by_symbol`; precalcular blocks en `prefetch_strat_a_secondary`; retorno extendido o mutación de cycle | P0 |
| `src/scanner.py` | Consumir `cycle.blocks_by_symbol`; quitar `detect_order_blocks` del bucle; eliminar `_fetch_ob_candles` | P0 |
| `tests/test_scan_prefetch.py` | Tests blocks, fallback, cache, equivalencia | P0 |
| `tests/test_scanner_strat_a.py` | Spy evaluate + cero fetch OB en evaluate | P0 |
| `tests/test_scanner.py` | Actualizar `test_scan_all_prefetches_before_eval` si aplica | P1 |
| `src/parallel_fetch.py` | Opcional: usar `fetch_candles_parallel` en secondary OB | P2 |
| `src/config.py` | Opcional: flag migración `OB_PREFETCH_WITH_PRIMARY` | P2 |
| `progress/impl_strat_a_ob_prefetch.md` | Mapa trazabilidad R→test | — |

**Sin cambios funcionales:** `strat_a.py` (ya acepta `blocks`), `candle_cache.py`
(TTL/clave ya correctos), algoritmo `detect_order_blocks`.

---

## 1. Extensión ScanCycleData (`scan_prefetch.py`)

```python
from strat_a import detect_order_blocks  # import lazy dentro de función si R4 circular

@dataclass
class ScanCycleData:
    ...
    blocks_by_symbol: dict[str, dict[str, list]] = field(default_factory=dict)
```

Tipo nominal: `dict[str, dict[str, list[OrderBlock]]]` — usar `TYPE_CHECKING` o
string annotation si evita import circular en module level.

---

## 2. Precálculo en prefetch_strat_a_secondary

Tras el bucle existente que pobla `candles_ob` / `ob_tf_labels`:

```python
blocks_by_symbol: dict[str, dict[str, list]] = {}
for sym in symbols:
    ob, label = _resolve_ob_candles(sym, raw_ob.get(sym, []), candles_5m_fallback)
    candles_ob[sym] = ob
    ob_tf_labels[sym] = label
    blocks_by_symbol[sym] = detect_order_blocks(ob)
```

**Firma propuesta** — extender retorno (menor diff que mutar cycle externamente):

```python
async def prefetch_strat_a_secondary(...) -> tuple[
    dict[str, list[Candle]],   # candles_ob
    dict[str, list[Candle]],   # candles_h1
    dict[str, str],            # ob_tf_labels
    dict[str, dict[str, list]],  # blocks_by_symbol  # NUEVO
]:
```

Alternativa: función wrapper `populate_blocks(candles_ob) -> blocks_by_symbol` en
`scan_prefetch.py` para tests unitarios aislados.

**Import circular (riesgo R4 prep):** si `scan_prefetch` → `strat_a` causa ciclo,
import lazy dentro de `prefetch_strat_a_secondary` o extraer `detect_order_blocks` a
`order_blocks.py` (solo si import falla en implementación).

---

## 3. Scanner — consumo y limpieza (`scanner.py`)

### `_scan_phase_prefetch`

```python
candles_ob, candles_h1, ob_tf_labels, blocks_by_symbol = await prefetch_strat_a_secondary(...)

return ScanCycleData(
    ...
    blocks_by_symbol=blocks_by_symbol,
)
```

### `_scan_phase_evaluate_assets` (~L1278–1281)

Reemplazar:

```python
# Antes
candles_ob = cycle.candles_ob.get(sym, candles)
ob_tf_label = cycle.ob_tf_labels.get(sym, "5m_fallback")
blocks = detect_order_blocks(candles_ob)

# Después
ob_tf_label = cycle.ob_tf_labels.get(sym, "5m_fallback")
blocks = cycle.blocks_by_symbol.get(sym, {"bull": [], "bear": []})
```

Mantener:
- `self.bot.order_blocks_by_asset[sym] = blocks` (radar R10)
- `cycle_ob_summary` usando `ob_tf_label` y blocks existentes
- Paso `blocks=blocks` a `evaluate_strat_a` (sin cambio de firma)

### Eliminar `_fetch_ob_candles` (R11)

Borrar método L297–314 y revisar imports `ORDER_BLOCK_*` en `scanner.py` — conservar
solo si usados en otro sitio.

Quitar import `detect_order_blocks` de `scanner.py` si ya no hay call sites.

---

## 4. Cache OB (`candle_cache.py`)

Sin cambio de código esperado. Verificación implementer:

- Clave: `(symbol, 180)`
- TTL: `CANDLE_CACHE_TTL_SEC = 300`
- `_fetch_with_optional_stagger` ya delega a `cache.get_or_update` en secondary
  prefetch

Test R17: mock que cuenta invocaciones `get_or_update` o `fetch_candles_with_retry`
con `tf_sec=180`.

---

## 5. Radar path (`radar_watch_tick`)

Sin prefetch OB dedicado en #21. Sigue leyendo `bot.order_blocks_by_asset` poblado
en último full scan. Staleness aceptable hasta próximo ciclo / umbral radar.

---

## 6. Refactor opcional `parallel_fetch` (P2)

```python
from parallel_fetch import fetch_candles_parallel

raw_ob = await fetch_candles_parallel(
    client, symbols, ORDER_BLOCK_TF_SEC, ORDER_BLOCK_CANDLES,
    concurrency=concurrency,
    timeout_sec=CANDLE_FETCH_TIMEOUT_SEC,
    cache=cache,
    retries=1,
)
```

H1 puede seguir en gather inline o segundo `fetch_candles_parallel`. No obligatorio
para cerrar acceptance.

---

## Alternativas descartadas

| Alternativa | Motivo de rechazo |
|-------------|-------------------|
| Fetch OB per-asset en evaluate (`_fetch_ob_candles`) | Viola R3; latencia O(N) en hot path |
| `detect_order_blocks` solo en evaluate | Viola R5/R6; CPU en fase incorrecta |
| Unificar OB en gather primario para todos los assets | Fetches OB desperdiciados; trade-off WS |
| Cambiar algoritmo OB o scoring en `strat_a.py` | Fuera de alcance SA-5 |
| Prefetch OB en cada `radar_watch_tick` | Scope futuro; I/O acotada pero no requerida |
| Mover H1 fuera de 3b | H1 ya funciona; no es gap #21 |

---

## Trazabilidad tests previstos

| R | Test propuesto |
|---|----------------|
| R1, R2 | `test_secondary_prefetch_only_for_symbol_subset` (existente, extender) |
| R4, R5, R14 | `test_secondary_prefetch_populates_blocks` |
| R6, R7, R19 | `test_evaluate_receives_precalculated_blocks` |
| R8, R16 | `test_ob_fallback_blocks_from_5m` |
| R9, R17 | `test_ob_cache_second_call_incremental` |
| R3, R11, R18 | `test_evaluate_phase_no_ob_network_io` |
| R5, R15 | `test_blocks_match_detect_order_blocks` |
| R10 | assert `order_blocks_by_asset` en test E2E scanner |
| R13 | extender `test_scan_all_prefetches_before_eval` (paralelismo) |
| R20 | suite completa pytest |
| R22 | `init.ps1` |

---

## Verificación reviewer

1. Log `[FASE 3b/5] Prefetch secundario OB+H1 — N símbolos` con N = len(strat_a_symbols).
2. `grep`/spy: cero `fetch_candles_with_retry(..., 180, ...)` en `_scan_phase_evaluate_assets`.
3. `grep`: sin `_fetch_ob_candles` en `scanner.py`.
4. Blocks inyectados en `ScanCycleData` llegan intactos a `evaluate_strat_a`.
5. Mock OB vacío (<6 velas) → label `5m_fallback` y blocks coherentes.
6. Segunda pasada prefetch OB → cache hit (menos fetches).
7. `init.ps1` verde; mapa en `progress/impl_strat_a_ob_prefetch.md`.

---

## Orden de implementación sugerido

1. Extender `ScanCycleData` + precalcular `blocks_by_symbol` en `prefetch_strat_a_secondary`.
2. Cablear retorno en `_scan_phase_prefetch`.
3. Consumir blocks en `_scan_phase_evaluate_assets`; eliminar `detect_order_blocks` del bucle.
4. Eliminar `_fetch_ob_candles`.
5. Tests prefetch + scanner (R14–R19).
6. (P2) Refactor `parallel_fetch` / log `blocks_precalc`.
7. `progress/impl_strat_a_ob_prefetch.md` + reviewer.