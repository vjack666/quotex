# Prep — Feature #21 `strat_a_ob_prefetch`

**Fecha:** 2026-07-02  
**Estado:** read-only prep (explorer) — listo para `spec_author`  
**Depende de:** #20 `strat_a_htf_zone_wiring`  
**Referencias:** `feature_list.json` id=21, `docs/ROADMAP_STRAT_A.md` SA-5, `src/scan_prefetch.py`, `src/parallel_fetch.py`, `src/candle_cache.py`, `src/scanner.py`, `progress/impl_scan_orchestration.md`

---

## Objetivo

Eliminar latencia OB en el hot path STRAT-A: velas 3m prefetchadas en paralelo, cacheadas con TTL, y **blocks precalculados** entregados a `evaluate_strat_a` sin `await fetch_candles` por activo en el bucle de evaluación.

**Criterio de rendimiento:** tiempo de scan por ciclo no debe crecer linealmente con N activos por I/O OB (medición en test o log `scan_fetch_elapsed_ms`).

---

## Gap analysis (estado actual)

### Lo que ya está hecho (post scan orchestration / feature #3)

| Pieza | Estado | Ubicación |
|-------|--------|-----------|
| Prefetch OB 3m en lote | ✅ parcial | `scan_prefetch.prefetch_strat_a_secondary()` — gather paralelo OB+H1 |
| Cache incremental OB | ✅ | `CandleCache.get_or_update()` vía `_fetch_with_optional_stagger` |
| Eval loop sin fetch OB | ✅ | `scanner._scan_phase_evaluate_assets` usa `cycle.candles_ob.get(sym)` (L1170) |
| Semáforo + concurrency | ✅ | `CANDLE_FETCH_CONCURRENCY` compartido con 5m/1m |
| Tests prefetch básicos | ✅ | `tests/test_scan_prefetch.py`, `test_scan_all_prefetches_before_eval` |

### Lo que falta vs `feature_list.json` / ROADMAP

| Gap | Severidad | Detalle |
|-----|-----------|---------|
| OB no está en el **mismo** gather que 5m/1m | media | Acceptance: *"prefetchan en paralelo con 5m/1m"* — hoy es fase **3b** separada tras filtrar `strat_a_symbols` |
| `detect_order_blocks` en bucle evaluate | baja (CPU) | Acceptance: *"evaluate_strat_a recibe blocks precalculados"* — hoy blocks se calculan en scanner L1172, no en prefetch |
| `_fetch_ob_candles` muerto | baja | Método async en `scanner.py` L249–266 — **no tiene call sites**; vestigio pre-orquestación |
| `parallel_fetch.py` sin uso | baja | Módulo #3 existe; `scan_prefetch` reimplementa gather+semáforo inline |
| `ScanCycleData` sin `blocks` | media | Solo dicts de velas; falta `blocks_by_symbol` / `ob_tf_labels` ya existen |
| Test explícito blocks → evaluate | media | No hay assert de que `evaluate_strat_a` recibe blocks del prefetch |
| Radar reusa blocks viejos | media | `radar_watch_tick` lee `bot.order_blocks_by_asset` (L1386) — OK si ciclo full actualizó; sin prefetch dedicado en tick |
| Métrica anti-O(N) I/O en evaluate | media | Falta test que el bucle evaluate haga 0 network calls OB |

### Flujo actual (resumen)

```
scan_all()
  FASE 1  _scan_phase_prepare()
  FASE 2  prefetch_primary_candles()     → 5m + 1m (gather único, todos los symbols)
  FASE 3b prefetch_strat_a_secondary() → OB 3m + H1 (solo strat_a_symbols ⊆ assets filtrados)
  FASE 3  _scan_phase_evaluate_assets()
            └─ por sym: candles_ob = cycle.candles_ob[sym]
                         blocks = detect_order_blocks(candles_ob)   # CPU en hot path
                         evaluate_strat_a(..., blocks=blocks, ...)
  FASE 4/5 selección + ejecución
```

**Conclusión:** #21 no es greenfield; es **cerrar gaps** entre implementación parcial (orquestación 2026-06-30) y acceptance literal del feature_list.

---

## Arquitectura objetivo

```
scan_all()
  FASE 2  prefetch_unified()  # propuesta
            asyncio.gather:
              por sym elegible: 5m, 1m, OB(3m)   # H1 puede quedar en 3b o mismo batch
            candle_cache en todos los TF
            blocks_by_symbol = {sym: detect_order_blocks(ob_candles)}
            ob_tf_labels por sym
  FASE 3  _scan_phase_evaluate_assets(cycle)
            └─ blocks = cycle.blocks_by_symbol[sym]   # sin detect_order_blocks
               evaluate_strat_a(..., blocks=blocks)
            └─ assert: ningún await fetch ORDER_BLOCK_TF_SEC en esta fase
```

**Alternativa aceptable (menor diff):** mantener fase 3b pero mover `detect_order_blocks` a `scan_prefetch` y extender `ScanCycleData`; unificar gather 5m+1m+OB solo si el spec prioriza latencia sobre simplicidad.

---

## Archivos a tocar

| Archivo | Cambio propuesto | Prioridad |
|---------|------------------|-----------|
| `src/scan_prefetch.py` | `ScanCycleData.blocks_by_symbol`; precalcular blocks post-fetch OB; opcional `prefetch_strat_a_unified()` | P0 |
| `src/scanner.py` | Consumir `cycle.blocks_by_symbol`; eliminar `_fetch_ob_candles`; quitar `detect_order_blocks` del bucle | P0 |
| `src/parallel_fetch.py` | Opcional: refactor `prefetch_*` para usar `fetch_candles_parallel` (DRY) | P2 |
| `src/candle_cache.py` | Sin cambio funcional; verificar clave `(asset, 180)` en cache OB | — |
| `src/strat_a.py` | Sin cambio — ya recibe `blocks: dict` | — |
| `src/config.py` | Opcional: `OB_PREFETCH_WITH_PRIMARY = True` flag migración | P2 |
| `tests/test_scan_prefetch.py` | Blocks precalculados; OB en gather primario (si aplica) | P0 |
| `tests/test_scanner_strat_a.py` | Cero fetch OB en evaluate; blocks mock en `ScanCycleData` | P0 |
| `tests/test_scanner.py` | Actualizar `test_scan_all_prefetches_before_eval` para nueva forma | P1 |
| `progress/impl_strat_a_ob_prefetch.md` | Trazabilidad (implementer) | — |

**No tocar:** `feature_list.json`, `specs/` (hasta spec_author), lógica `detect_order_blocks` en `strat_a.py`.

---

## Puntos de integración detallados

### 1. `ScanCycleData` — extensión

```python
@dataclass
class ScanCycleData:
    ...
    blocks_by_symbol: dict[str, dict[str, list[OrderBlock]]] = field(default_factory=dict)
```

Poblar en `prefetch_strat_a_secondary` (o nuevo unified prefetch):

```python
from strat_a import detect_order_blocks, OrderBlock  # o mover helper a módulo neutral

for sym in symbols:
    ob_candles, label = _resolve_ob_candles(sym, raw_ob.get(sym, []), candles_5m_fallback)
    candles_ob[sym] = ob_candles
    ob_tf_labels[sym] = label
    blocks_by_symbol[sym] = detect_order_blocks(ob_candles)
```

### 2. `scanner._scan_phase_evaluate_assets`

Reemplazar bloque L1170–1173:

```python
# Antes
candles_ob = cycle.candles_ob.get(sym, candles)
blocks = detect_order_blocks(candles_ob)

# Después
blocks = cycle.blocks_by_symbol.get(sym, {"bull": [], "bear": []})
ob_tf_label = cycle.ob_tf_labels.get(sym, "5m_fallback")
```

Mantener `self.bot.order_blocks_by_asset[sym] = blocks` para radar.

### 3. Eliminar `_fetch_ob_candles`

- Borrar método L249–266 y imports asociados si quedan huérfanos.
- Actualizar `specs/strat_a_evaluate/design.md` referencia obsoleta (en fase spec, no en prep).

### 4. Unificar prefetch OB con 5m/1m (opción rendimiento)

Hoy `symbols_needing_strat_a_prefetch` excluye activos sin 5m suficientes — OB solo se pide para subconjunto **después** de tener 5m. Para un solo gather:

1. Prefetch 5m+1m para todos los `symbols`.
2. Calcular `strat_a_symbols` con mismas reglas.
3. Segundo mini-gather solo OB para `strat_a_symbols` **en paralelo** con inicio de evaluate de activos no-STRAT-A (complejo).

**Recomendación spec:** Opción pragmática — **mantener 3b** pero precalcular blocks ahí; renombrar acceptance a *"sin fetch OB en evaluate"* como criterio primario. Si product owner exige literal *"con 5m/1m"*, fusionar en `prefetch_primary_candles` añadiendo 3ª task OB por symbol (coste: +N fetches para activos que nunca llegan a STRAT-A).

### 5. `parallel_fetch.py` vs `scan_prefetch.py`

`parallel_fetch.fetch_candles_parallel(client, symbols, tf_sec, count, cache=...)` cubre un solo TF.

Propuesta DRY:

```python
# En scan_prefetch
from parallel_fetch import fetch_candles_parallel

raw_ob = await fetch_candles_parallel(
    client, symbols, ORDER_BLOCK_TF_SEC, ORDER_BLOCK_CANDLES,
    concurrency=concurrency, timeout_sec=..., cache=cache, retries=1,
)
```

Elimina duplicación de semáforo en secondary prefetch. **No obligatorio** para cerrar #21.

### 6. `candle_cache.py` — TTL OB

- Clave: `(asset, ORDER_BLOCK_TF_SEC)` donde `ORDER_BLOCK_TF_SEC = 180`.
- TTL: `CANDLE_CACHE_TTL_SEC = 300` — coherente con acceptance.
- Incremental fetch en hits — ya implementado; validar en test que segunda llamada no hace full fetch (mock contador).

### 7. Radar path (`radar_watch_tick`)

- Sigue usando `order_blocks_by_asset` poblado en último full scan.
- **Gap:** entre full scans, blocks pueden envejecer hasta `STRAT_A_RADAR_FULL_SCAN_MIN_SEC` (180s).
- Opciones spec: (a) aceptar staleness; (b) prefetch OB solo para símbolos en `radar_watchlist` en tick (I/O acotada). Fuera del happy path #21 si full scan frecuente.

---

## Riesgos

| ID | Riesgo | Severidad | Mitigación |
|----|--------|-----------|------------|
| R1 | Unificar gather → más fetches OB inútiles | media | Mantener subconjunto `strat_a_symbols` |
| R2 | `detect_order_blocks` en prefetch aumenta CPU fase 2 | baja | Es O(n) velas, n≈55; negligible vs WS |
| R3 | Romper `test_scan_all_prefetches_before_eval` | media | Actualizar conteos expected (primary+secondary) |
| R4 | Circular import `scan_prefetch` → `strat_a` | media | Import lazy de `detect_order_blocks` o extraer OB detect a `order_blocks.py` |
| R5 | Cache OB stale tras ruptura violenta | baja | TTL 300s; full scan cada ciclo refresca |
| R6 | Regresión fallback 5m | media | Conservar `_resolve_ob_candles`; test `len(ob)<6 → 5m_fallback` |
| R7 | Concurrencia WS con HTF #20 | baja | Semáforos independientes; OB usa `CANDLE_FETCH_CONCURRENCY` |

---

## Tests sugeridos

### `tests/test_scan_prefetch.py`

| Test | Verifica |
|------|----------|
| `test_secondary_prefetch_populates_blocks` | `blocks_by_symbol[sym]` tiene keys `bull`/`bear` |
| `test_ob_fallback_blocks_from_5m` | Mock OB vacío → blocks calculados sobre 5m fallback |
| `test_blocks_match_detect_order_blocks` | Resultado idéntico a llamada directa en scanner (regresión) |
| `test_ob_cache_second_call_incremental` | Mock cache hit; un solo full fetch por (sym, 180) |

### `tests/test_scanner_strat_a.py` / `test_scanner.py`

| Test | Verifica |
|------|----------|
| `test_evaluate_phase_no_ob_network_io` | Monkeypatch `fetch_candles_with_retry` → assert 0 calls con `tf=180` durante `_scan_phase_evaluate_assets` |
| `test_evaluate_receives_precalculated_blocks` | Inject blocks conocidos en `ScanCycleData`; spy `evaluate_strat_a` recibe mismos blocks |
| `test_scan_time_sublinear_ob` | Extender `test_scan_all_prefetches_before_eval`: `prefetch_span < sequential * 0.75` con N=4 activos |

### Regresión `evaluate_strat_a`

- Tests existentes en `test_strat_a.py` pasan blocks explícitos — sin cambio.
- E2E scanner STRAT-A (#18) debe seguir verde tras eliminar `_fetch_ob_candles`.

### Verificación

```powershell
python -m pytest tests/test_scan_prefetch.py tests/test_scanner.py tests/test_scanner_strat_a.py -q
.\init.ps1
```

Log esperado (ya parcialmente presente):

```
[FASE 3b/5] Prefetch secundario OB+H1 — N símbolos
⚡ Prefetch velas: scan_fetch_elapsed_ms=... | activos=N | concurrency=2
```

Post-#21: añadir `blocks_precalc=N` en log opcional.

---

## Mapeo a criterios de aceptación

| Criterio `feature_list` | Estado actual | Acción #21 |
|-------------------------|---------------|------------|
| Velas OB 3m prefetch paralelo con 5m/1m | ⚠️ paralelo en 3b, no mismo gather | Unificar o documentar 3b como cumplimiento |
| Sin `await fetch_candles` OB en bucle activo | ✅ evaluate limpio | Eliminar `_fetch_ob_candles`; test spy |
| Cache OB por activo TTL coherente | ✅ `CandleCache` | Test incremental |
| Tests: blocks llegan a `evaluate_strat_a` | ❌ | Nuevos tests |
| `init.ps1` verde | — | Suite completa |

---

## Orden de implementación sugerido

1. Extender `ScanCycleData` + precalcular `blocks_by_symbol` en `prefetch_strat_a_secondary`.
2. Consumir blocks en `scanner._scan_phase_evaluate_assets`; eliminar `detect_order_blocks` del bucle.
3. Eliminar `_fetch_ob_candles` (dead code).
4. Tests prefetch + scanner (no I/O OB en evaluate).
5. (Opcional P2) Refactor a `parallel_fetch.fetch_candles_parallel`.
6. (Opcional P2) Fusionar OB en `prefetch_primary_candles` si spec lo exige literalmente.
7. `progress/impl_strat_a_ob_prefetch.md` + reviewer.

---

## Comparativa: antes vs después

| Métrica | Pre-orquestación | Hoy (2026-07) | Objetivo #21 |
|---------|------------------|---------------|--------------|
| Fetch OB en evaluate | `await _fetch_ob_candles` por sym | Ninguno (prefetch 3b) | Confirmado + test |
| `detect_order_blocks` | En evaluate | En evaluate | En prefetch |
| `parallel_fetch` usado | No | No | Opcional DRY |
| Blocks en `ScanCycleData` | N/A | No | Sí |
| Código muerto `_fetch_ob_candles` | N/A | Sí | Eliminado |

---

## Fuera de alcance (#21)

- HTF 15m / zone_memory (#20).
- Cambiar algoritmo `detect_order_blocks` o scoring OB en `strat_a.py`.
- Prefetch H1 (ya en 3b; no requiere mover).
- Radar tick prefetch OB dedicado (mejora futura).
- Validación demo (#22).

---

## Notas para `spec_author`

1. **Decisión clave:** ¿acceptance *"paralelo con 5m/1m"* exige un solo `asyncio.gather` o basta fase 3b sin I/O en evaluate? Prep recomienda **cerrar con 3b + blocks precalculados** salvo presión de latencia.
2. Si se unifica gather, definir si OB se pide para **todos** los assets o solo `strat_a_symbols` (trade-off WS).
3. Coordinar con #20: no competir por semáforo; OB usa `candle_cache` del bot, HTF cache propio.
4. Actualizar diagrama fases en `impl_scan_orchestration.md` tras implementar.