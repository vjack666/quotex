# Design — strat_a_htf_zone_wiring

> Feature id=20. Fase SA-4 — cablear `HTFScanner` y `zone_memory` en STRAT-A.
> Referencias: `docs/ROADMAP_STRAT_A.md` (SA-4), `progress/prep_strat_a_htf_zone.md`,
> `src/htf_scanner.py`, `src/zone_memory.py`, `src/scanner.py`,
> `src/entry_decision_engine.py`, `src/entry_scorer.py`, `src/consolidation_bot.py`.
> Depende de #19 (`strat_a_quality_filters`, done).

---

## Objetivo

Conectar módulos **ya implementados pero desconectados** para que STRAT-A opere con
contexto 15m real y memoria histórica de zonas. Principio *reject-first*: veto HTF
y muro `zone_memory` ocurren **antes** de `score_candidate` / `select_best`.

| Componente | Estado actual | Objetivo (#20) |
|------------|---------------|----------------|
| `HTFScanner` | Existe, no instanciado | Tarea asyncio en background |
| Lectura 15m en scan | No usada | `get_candles_15m(sym)` sync, sin I/O |
| Veto tendencia 15m | Solo en `entry_decision_engine` | Aplicado en scanner (2 rutas) |
| `candidate.zone_memory` | Siempre `[]` | `query_nearby_zones` desde journal |
| `score_breakdown["zone_memory"]` | Siempre 0 | Refleja historia cuando existe |
| `_score_trend` | Usa velas 5m | Prefiere 15m si ≥25 velas |

**Fuera de alcance (#21+):** prefetch OB 3m, refactor completo a
`entry_decision_engine` como único gate, cambios en reglas de `zone_memory.py`,
validación demo (#22).

---

## Arquitectura objetivo

```
consolidation_bot.main()
  └─ asyncio.create_task(bot.htf_scanner.run_forever())

scanner._scan_phase_evaluate_assets / radar_watch_tick
  └─ por activo STRAT-A con has_signal=True:
       ├─ candles_15m = bot.htf_scanner.get_candles_15m(sym)
       ├─ veto HTF (_check_htf_available_and_aligned)
       ├─ zones = query_nearby_zones(db, sym, price)
       ├─ veto muro si score_zone_memory(zones, ...) <= -10
       ├─ candidate = _candidate_from_strat_a_evaluation(...)
       ├─ candidate.zone_memory = zones
       ├─ candidate.candles_15m = candles_15m
       └─ score_candidate(candidate)  # trend 15m + zone_memory adj
```

**Warm-up HTF:** al arranque el cache puede estar vacío ~60s hasta el primer ciclo
HTF. Política elegida: **rechazo estricto** (`len < 10` → veto). Sin grace period —
alineado con acceptance *"0 entradas sin HTF alineado"* y ROADMAP SA-4.

---

## Archivos a modificar

| Archivo | Cambio | Prioridad |
|---------|--------|-----------|
| `src/htf_scanner.py` | Fix import `connection.fetch_candles_with_retry`; corregir docstring de import | P0 |
| `src/consolidation_bot.py` | `self.htf_scanner`, `self._htf_task`; `create_task` en `main`; cancel en shutdown | P0 |
| `src/scanner.py` | Helper gates HTF+zone_memory; veto en scan + radar; poblar campos; logs/stats | P0 |
| `src/models.py` | Campo `candles_15m: List[Candle]` en `CandidateEntry` | P1 |
| `src/entry_scorer.py` | `_score_trend`: preferir `entry.candles_15m` si `len >= 25` | P1 |
| `src/instrumentation_layer.py` | Incrementar `gate_htf_reject` en vetos HTF | P2 |
| `hub/hub_scanner.py` | Callback `on_asset_refresh` → `update_htf_status` | P2 |
| `tests/test_htf_zone_wiring.py` | Nuevo — unitarios HTF + zone_memory + import | P0 |
| `tests/test_scanner_strat_a.py` | Extender E2E: rechazo HTF, zone_memory en breakdown | P0 |
| `progress/impl_strat_a_htf_zone.md` | Mapa trazabilidad R→test (implementer) | — |

**Sin cambios:** `zone_memory.py`, `strat_a.py` (evaluación pura 5m/1m),
`entry_decision_engine.py` (solo reutilizar helpers privados).

---

## Fix import roto (R3, R21)

`htf_scanner._fetch_15m` (línea ~267) importa lazy desde `consolidation_bot`;
tras refactor #1 la función vive en `connection.py`. Cambio:

```python
from connection import fetch_candles_with_retry
```

Corregir docstring de uso: `from htf_scanner import HTFScanner` (no `src.`).

---

## Arranque HTFScanner (`consolidation_bot.py`)

### `ConsolidationBot.__init__`

```python
from htf_scanner import HTFScanner
from connection import get_open_assets
from config import STRAT_A_MIN_PAYOUT

self.htf_scanner = HTFScanner(
    client,
    assets_fn=lambda: get_open_assets(client, min_payout=STRAT_A_MIN_PAYOUT),
    min_payout=STRAT_A_MIN_PAYOUT,
    on_asset_refresh=self._on_htf_asset_refresh,  # P2 HUB, opcional stub
)
self._htf_task: asyncio.Task | None = None
```

`get_open_assets` usa `payout >= min_payout`; alinear `HTFScanner._default_assets_scan`
(estricto `>`) documentando coherencia con #19 o unificar a `>=` en `htf_scanner`
si tests lo exigen.

### `main()` — tras crear bot

```python
bot._htf_task = asyncio.create_task(bot.htf_scanner.run_forever())
log.info("[HTF] Scanner 15m iniciado en background")
```

### `shutdown_background_tasks`

```python
if self._htf_task and not self._htf_task.done():
    self._htf_task.cancel()
    try:
        await self._htf_task
    except asyncio.CancelledError:
        pass
await self.executor.shutdown_background_tasks()
```

---

## Helper de gates en scanner (R7–R10, R12, R16)

Centralizar en método privado para evitar bypass radar (riesgo R6 del prep):

```python
from entry_decision_engine import (
    _check_htf_available_and_aligned,
    _check_zone_memory_no_wall,
)
from strat_a import infer_h1_trend
from zone_memory import query_nearby_zones, score_zone_memory
from trade_journal import get_journal

def _apply_strat_a_htf_zone_gates(
    self,
    sym: str,
    direction: str,
    price: float,
) -> tuple[bool, list, list, str | None]:
    """
    Retorna (passed, candles_15m, zones, skip_reason).
    passed=False → caller hace continue sin candidato.
    """
    candles_15m = self.bot.htf_scanner.get_candles_15m(sym)
    veto, _htf_trend = _check_htf_available_and_aligned(
        candles_15m, direction, infer_h1_trend,
    )
    if not veto.passed:
        log.info("⛔ [STRAT-A] %s: %s", sym, veto.reason)
        self._bump_strat_a_skip_stats("htf_reject")
        return False, candles_15m, [], "htf_reject"

    journal = get_journal()
    zones = query_nearby_zones(journal.db_path, sym, price)
    zone_adj = score_zone_memory(zones, direction, price) if zones else 0.0
    wall = _check_zone_memory_no_wall(zone_adj, -10.0)
    if not wall.passed:
        log.info("⛔ [STRAT-A] %s: zone_memory wall (adj=%.1f)", sym, zone_adj)
        self._bump_strat_a_skip_stats("zone_memory_wall")
        return False, candles_15m, zones, "zone_memory_wall"

    return True, candles_15m, zones, None
```

**Ubicación llamada (ruta principal):** en `_scan_phase_evaluate_assets`, después de
`if not ev.has_signal: continue` implícito — es decir, cuando `ev.has_signal` es
True, **antes** de `_candidate_from_strat_a_evaluation` (~línea 1294).

**Ubicación llamada (radar):** en `radar_watch_tick`, cuando `ev.has_signal` es True,
antes de `_candidate_from_strat_a_evaluation` (~línea 1462).

Extender `_bump_strat_a_skip_stats` para reconocer `htf_reject` y
`zone_memory_wall` (incrementar `skipped`).

---

## Construcción de candidato (R12–R15)

Tras gates exitosos:

```python
passed, candles_15m, zones, skip = self._apply_strat_a_htf_zone_gates(sym, ev.direction, price)
if not passed:
    continue

candidate = self._candidate_from_strat_a_evaluation(...)
candidate.zone_memory = zones
candidate.candles_15m = candles_15m
score_candidate(candidate)
```

Alternativa: pasar `zones` y `candles_15m` como parámetros a
`_candidate_from_strat_a_evaluation` — preferir asignación post-creación para
mínimo diff.

### `models.py`

```python
candles_15m: List[Candle] = field(default_factory=list)
```

### `entry_scorer.py` — trend 15m

```python
HTF_TREND_MIN_CANDLES = 25  # o constante en config/htf_scanner

trend_candles = (
    entry.candles_15m
    if len(getattr(entry, "candles_15m", [])) >= HTF_TREND_MIN_CANDLES
    else entry.candles
)
s_trend = _score_trend(trend_candles, entry.direction, w["trend"])
```

Si HTF vacío, el veto R7 ya rechazó — no hay inconsistencia con fallback 5m.

---

## Instrumentación y HUB (P2, no bloquea cierre)

- En veto HTF: `instrumentation.gate_htf_reject += 1` si layer accesible desde bot.
- `_on_htf_asset_refresh`: delegar a `hub_scanner.update_htf_status` si HUB activo.

---

## Alternativas descartadas

| Alternativa | Motivo de rechazo |
|-------------|-------------------|
| Fetch 15m síncrono por activo en scan loop | Viola R5/R6; compite con WS; latencia en hot path |
| Grace period HTF 120–180s al boot | Permite entradas sin HTF alineado; contradice acceptance y ROADMAP |
| Refactor completo a `evaluate_entry()` como único gate | Duplica vetos #19; scope mayor que #20 |
| Solo scoring zone_memory sin veto muro | ROADMAP/PLAN MAESTRO y `_check_zone_memory_no_wall` exigen bloqueo duro |
| Modificar `evaluate_strat_a` para HTF | Viola capa estrategia pura; HTF es contexto de pipeline, no señal 5m |
| Duplicar lógica `_check_htf_*` en scanner | Reutilizar helpers de `entry_decision_engine` evita drift |

---

## Trazabilidad tests previstos

| R | Test propuesto |
|---|----------------|
| R1, R2 | `test_htf_task_started_and_cancelled_on_shutdown` (o inspección + test bot mock) |
| R3, R21 | `test_htf_scanner_fetch_import` |
| R4, R5, R6 | `test_scan_uses_htf_cache_not_fetch` |
| R7, R17 | `test_htf_veto_missing_candles` |
| R8, R18 | `test_htf_veto_misaligned_put` / `test_scan_rejects_without_htf_alignment` |
| R9 | `test_htf_pass_aligned_call` |
| R10 | cubierto por `test_scan_rejects_without_htf_alignment` (radar) |
| R11 | assert log en tests E2E |
| R12, R19 | `test_zone_memory_populated_from_db` |
| R13 | `test_score_breakdown_zone_memory_nonzero` |
| R14, R15 | `test_score_trend_uses_15m_candles` (unit scorer o E2E) |
| R16 | `test_zone_memory_wall_veto` |
| R22 | suite completa pytest |
| R24 | `init.ps1` |

---

## Verificación reviewer

1. Log `[HTF] Scanner 15m iniciado` al arrancar bot.
2. Señal CALL con 15m bearish: 0 candidatos, log `⛔ [STRAT-A] ... HTF`.
3. Cache vacío (`[]`): rechazo, sin candidato.
4. Journal con `expired_zones` fixture: `zone_memory` poblado y breakdown ≠ 0.
5. Spy: cero `fetch_candles_with_retry(tf_sec=900)` en fase evaluate.
6. Radar y scan principal aplican mismo veto HTF.
7. `init.ps1` verde; mapa en `progress/impl_strat_a_htf_zone.md`.