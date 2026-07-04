# Prep — Feature #20 `strat_a_htf_zone_wiring`

**Fecha:** 2026-07-02  
**Estado:** read-only prep (explorer) — listo para `spec_author`  
**Depende de:** #19 `strat_a_quality_filters` (spec_ready)  
**Referencias:** `feature_list.json` id=20, `docs/ROADMAP_STRAT_A.md` SA-4, `src/htf_scanner.py`, `src/zone_memory.py`, `src/scanner.py`, `src/entry_scorer.py`, `src/entry_decision_engine.py`

---

## Objetivo

Cablear los módulos **ya implementados pero desconectados**:

1. **`HTFScanner`** — cache 15m en background, lectura no bloqueante en el scan loop.
2. **`zone_memory`** — consulta `expired_zones` del journal y población de `candidate.zone_memory` para scoring/veto.

Resultado esperado: STRAT-A opera con contexto 15m real y memoria histórica de zonas; entradas contra tendencia 15m se rechazan; `score_breakdown["zone_memory"]` refleja historia cuando existe.

---

## Gap analysis (estado actual)

| Componente | Existe | Cableado al pipeline | Evidencia |
|------------|--------|----------------------|-----------|
| `HTFScanner` (`htf_scanner.py`) | ✅ | ❌ | No hay `create_task(htf.run_forever())` en `consolidation_bot.main()` ni atributo en `ConsolidationBot` |
| `get_candles_15m(sym)` | ✅ | ❌ | `scanner.py` no importa ni llama HTF |
| Tendencia 15m → veto | ✅ (lógica) | ❌ | `entry_decision_engine._check_htf_available_and_aligned()` existe; scanner no lo usa |
| `_score_trend` con 15m | ✅ (función) | ❌ | `entry_scorer._score_trend()` usa `entry.candles` (5m), no 15m |
| `zone_memory.query_nearby_zones` | ✅ | ❌ | Nunca invocado desde `scanner.py` |
| `CandidateEntry.zone_memory` | ✅ (campo) | ❌ | Siempre `[]` — `_candidate_from_strat_a_evaluation` no lo asigna |
| `score_zone_memory` en scorer | ✅ | ⚠️ parcial | `_score_zone_memory_adj()` listo; retorna 0.0 sin datos |
| `expired_zones` en journal | ✅ | ✅ (escritura) | `scanner._merge_zone_state` / `log_expired_zone` ya persisten zonas |
| Telemetría HUB HTF | ✅ (API) | ❌ | `hub_scanner.update_htf_status()` existe; sin callback `on_asset_refresh` |
| Instrumentación `gate_htf_reject` | ✅ (campos) | ❌ | `instrumentation_layer.py` tiene contadores; no incrementados |

### Bugs / deuda detectada (bloquean wiring)

1. **`htf_scanner._fetch_15m`** importa `fetch_candles_with_retry` desde `consolidation_bot` (línea 267), pero tras el refactor (#1) esa función vive en `connection.py`. El import lazy fallará al primer fetch 15m.
2. **`htf_scanner` docstring** usa `from src.htf_scanner import HTFScanner`; en runtime el path es `src/` en `sys.path` → import directo `from htf_scanner import HTFScanner`.
3. **Payout HTF vs scan:** `_default_assets_scan` usa `payout > min_payout` (estricto); `get_open_assets` usa `>=`. Alinear con `STRAT_A_MIN_PAYOUT` post-#19.

### Qué ya funciona (no reimplementar)

- H1 confirm en `evaluate_strat_a` (`h1_conflict`) — independiente de HTF 15m.
- Prefetch 5m/1m/OB/H1 en fases (`scan_prefetch.py`) — fuera de alcance #20.
- Scoring zone_memory en `score_candidate` — solo falta poblar `zone_memory`.

---

## Arquitectura objetivo

```
consolidation_bot.main()
  └─ asyncio.create_task(bot.htf_scanner.run_forever())   # background 15m

scanner.scan_all()
  ├─ _scan_phase_prefetch()          # sin cambio HTF (15m viene del cache)
  └─ _scan_phase_evaluate_assets()
       └─ por activo STRAT-A con señal:
            ├─ candles_15m = bot.htf_scanner.get_candles_15m(sym)   # sync, no I/O
            ├─ veto HTF si missing/misaligned/flat
            ├─ candidate.zone_memory = query_nearby_zones(db, sym, price)
            ├─ score_candidate(candidate)   # trend 15m + zone_memory adj
            └─ logs + journal metadata (htf_aligned, zone_memory_adj)
```

**Principio reject-first:** el veto HTF debe ocurrir **antes** de `score_candidate` / `select_best`, con `skip_reason` o log explícito (`htf_missing`, `htf_misaligned`).

---

## Archivos a tocar

| Archivo | Cambio propuesto | Prioridad |
|---------|------------------|-----------|
| `src/htf_scanner.py` | Corregir import → `connection.fetch_candles_with_retry` | P0 |
| `src/consolidation_bot.py` | `self.htf_scanner`, `self._htf_task`; iniciar/cancelar en `main` / `shutdown_background_tasks` | P0 |
| `src/scanner.py` | Leer 15m cache; veto HTF; `query_nearby_zones`; asignar `zone_memory`; stats/logs | P0 |
| `src/models.py` | Opcional: `candles_15m: List[Candle]` en `CandidateEntry` | P1 |
| `src/entry_scorer.py` | `_score_trend`: preferir `entry.candles_15m` si ≥25 velas | P1 |
| `src/config.py` | `HTF_ENABLED`, `HTF_MIN_CANDLES`, `HTF_ALIGN_REQUIRED` (o reutilizar constantes de `htf_scanner`) | P1 |
| `src/instrumentation_layer.py` | Incrementar `gate_htf_reject` / `assets_from_htf` en vetos | P2 |
| `hub/hub_scanner.py` | Callback `on_asset_refresh` → `update_htf_status` | P2 |
| `tests/test_htf_zone_wiring.py` | Nuevo — mocks HTF + journal SQLite temporal | P0 |
| `tests/test_scanner_strat_a.py` | Extender E2E: rechazo HTF, zone_memory en breakdown | P0 |
| `progress/impl_strat_a_htf_zone.md` | Trazabilidad R→test (implementer) | — |

**Sin cambios esperados:** `zone_memory.py` (lógica completa), `strat_a.py` (evaluación pura 5m/1m), `feature_list.json` (hasta reviewer).

**Opcional (evaluar en spec):** integrar `entry_decision_engine.evaluate_entry()` como único gate post-scoring. Hoy duplicaría vetos de #19; recomendación: **veto HTF inline en scanner** + reutilizar helpers de `entry_decision_engine` importando `_check_htf_available_and_aligned` y `_check_zone_memory_no_wall`.

---

## Puntos de integración detallados

### 1. Arranque `HTFScanner` (`consolidation_bot.py`)

```python
# ConsolidationBot.__init__
from htf_scanner import HTFScanner
from connection import get_open_assets

self.htf_scanner = HTFScanner(
    client,
    assets_fn=lambda: get_open_assets(client, min_payout=HTF_MIN_PAYOUT),
    min_payout=HTF_MIN_PAYOUT,  # alinear con STRAT_A_MIN_PAYOUT tras #19
    on_asset_refresh=self._on_htf_asset_refresh,  # opcional HUB
)
self._htf_task: asyncio.Task | None = None

# consolidation_bot.main(), tras crear bot:
bot._htf_task = asyncio.create_task(bot.htf_scanner.run_forever())

# shutdown_background_tasks / finally:
if bot._htf_task: bot._htf_task.cancel()
```

**Riesgo:** segundo loop de fetch 15m compite con WS del scan. Mitigación ya presente: semáforo propio (`Semaphore(2)`), `HTF_INTER_ASSET_SLEEP=0.4`, TTL 870s.

### 2. Lectura 15m en scanner (sin fetch bloqueante)

Ubicación: `scanner._scan_phase_evaluate_assets`, **después** de `ev.has_signal` y **antes** de `_candidate_from_strat_a_evaluation` (líneas ~1248–1254).

```python
candles_15m = self.bot.htf_scanner.get_candles_15m(sym)
veto, htf_trend = _check_htf_available_and_aligned(
    candles_15m, ev.direction, infer_h1_trend,
)
if not veto.passed:
    log.info("⛔ %s: %s", sym, veto.reason)
    self._bump_strat_a_skip_stats("htf_reject")  # nuevo reason
    continue
```

Reutilizar `infer_h1_trend` de `strat_a.py` (misma heurística EMA que H1; coherente con `entry_decision_engine`).

**Warm-up:** al inicio de sesión el cache puede estar vacío → rechazo `HTF_MISSING` hasta primer ciclo HTF (~60s + fetches). Documentar en spec; opción `HTF_GRACE_SEC` para demo.

### 3. Zone memory en candidato

```python
from zone_memory import query_nearby_zones

journal = get_journal()
zones = query_nearby_zones(journal.db_path, sym, price)
candidate = self._candidate_from_strat_a_evaluation(...)
candidate.zone_memory = zones
candidate.candles_15m = candles_15m  # si se añade campo
score_candidate(candidate)
```

**Veto muro histórico (opcional pero alineado PLAN MAESTRO):**

```python
zone_adj = score_zone_memory(zones, ev.direction, price) if zones else 0.0
if zone_adj <= -10.0:
    log.info("⛔ %s: zone_memory wall (adj=%.1f)", sym, zone_adj)
    continue
```

O delegar a `_check_zone_memory_no_wall` de `entry_decision_engine`.

### 4. Trend score con 15m (`entry_scorer.py`)

Hoy `_score_trend(entry.candles, ...)` usa velas 5m (peso 25 en rebound / 30 en breakout).

Propuesta mínima:

```python
trend_candles = entry.candles_15m if len(getattr(entry, "candles_15m", [])) >= 25 else entry.candles
s_trend = _score_trend(trend_candles, entry.direction, w["trend"])
```

Si se usa fallback 5m por HTF vacío, el veto HTF ya habrá rechazado — no hay inconsistencia.

### 5. Radar watchlist (`scanner.radar_watch_tick`)

Segunda ruta STRAT-A (líneas ~1346–1428): **también** necesita HTF + zone_memory en candidatos radar, o veto explícito. Hoy reutiliza `order_blocks_by_asset` cacheados; aplicar mismo patrón para 15m cache.

### 6. Journal / logging

- `trade_journal.log_candidate` ya soporta `new_htf_aligned`, `new_zone_memory_adj` en shadow audit.
- Pasar esos campos al loguear candidatos aceptados/rechazados en fase 4/5.
- Log candidato existente (línea ~1537) podría añadir `htf=%s zm=%+.1f`.

---

## Riesgos

| ID | Riesgo | Severidad | Mitigación |
|----|--------|-----------|------------|
| R1 | Import roto en `htf_scanner._fetch_15m` | **alta** | Fix P0 antes de `create_task` |
| R2 | Cache 15m vacío al boot → 0 señales STRAT-A | media | Grace period o log `[HTF] warming up`; HUB muestra `htf_candles=0` |
| R3 | Contención WS (HTF + prefetch 5m) | media | Semáforos separados; HTF TTL largo; no fetch 15m en hot path |
| R4 | `expired_zones` vacío en DB nueva → zone_memory siempre 0 | baja | Test con fixture SQLite; aceptable en demo fría |
| R5 | Duplicar lógica veto vs `entry_decision_engine` | media | Importar helpers privados o thin wrapper `check_strat_a_htf()` |
| R6 | Radar sin HTF → bypass del filtro | media | Misma función `_apply_htf_zone_gates()` en ambas rutas |
| R7 | TZ en `zone_memory._ts_to_iso` (UTC-3) vs journal | baja | Ya alineado con `BROKER_TZ`; validar en test |

---

## Tests sugeridos

### Unitarios (`tests/test_htf_zone_wiring.py`)

| Test | Verifica |
|------|----------|
| `test_htf_veto_missing_candles` | `len(candles_15m) < 10` → rechazo, candidato no creado |
| `test_htf_veto_misaligned_put` | 15m bullish + direction put → rechazo |
| `test_htf_pass_aligned_call` | 15m bullish + call → continúa pipeline |
| `test_zone_memory_populated_from_db` | Fixture `expired_zones` → `candidate.zone_memory` no vacío |
| `test_score_breakdown_zone_memory_nonzero` | Con zona histórica relevante → `score_breakdown["zone_memory"] != 0` |
| `test_zone_memory_wall_veto` | `score_zone_memory` ≤ -10 → skip |
| `test_htf_scanner_fetch_import` | Mock `connection.fetch_candles_with_retry`; `HTFScanner._fetch_15m` no lanza ImportError |

### E2E scanner (`tests/test_scanner_strat_a.py`)

| Test | Verifica |
|------|----------|
| `test_scan_rejects_without_htf_alignment` | Mock `bot.htf_scanner.get_candles_15m` bearish; señal CALL → 0 candidatos |
| `test_scan_uses_htf_cache_not_fetch` | Spy: ningún `fetch` con `tf_sec=900` en fase evaluate |
| `test_scan_htf_task_started` | Mock bot con `htf_scanner`; verificar wiring en integración bot (opcional) |

### Fixtures

- **HTF mock:** clase fake con `get_candles_15m` devolviendo 30 velas sintéticas bullish/bearish.
- **Journal mock:** SQLite in-memory con tabla `expired_zones` (copiar DDL de `trade_journal.py`).
- Reutilizar helpers de `tests/test_strat_a.py` (`_candle`, zonas).

### Verificación manual

```powershell
python -m pytest tests/test_htf_zone_wiring.py tests/test_scanner_strat_a.py -q
.\init.ps1
```

Dry-run: buscar en log `⛔ ... HTF` y `[HTF] Scanner 15m iniciado`.

---

## Mapeo a criterios de aceptación (`feature_list.json`)

| Criterio | Cómo verificar |
|----------|----------------|
| HTFScanner arranca como tarea asyncio | `create_task` en `main`; test o inspección |
| `htf.get_candles_15m(sym)` sin fetch bloqueante | Spy en evaluate; cero awaits 15m en bucle |
| `candidate.zone_memory` vía `query_nearby_zones` | Assert en test E2E |
| Entrada contra 15m → rechazo | Test misaligned + live log |
| Tests con mocks HTF y journal | `test_htf_zone_wiring.py` |
| `init.ps1` verde | Suite completa |

---

## Orden de implementación sugerido

1. Fix import `htf_scanner` → `connection` (desbloquea background fetch).
2. Instanciar + `create_task` en `consolidation_bot`; cancel en shutdown.
3. Helper `_check_strat_a_htf(sym, direction)` en `scanner.py` (o import EDE helpers).
4. Veto HTF en ruta principal + radar.
5. Poblar `zone_memory` + veto muro opcional.
6. `entry_scorer` trend 15m + campo `candles_15m` en `CandidateEntry`.
7. Tests + logs journal + HUB callback (P2).
8. `progress/impl_strat_a_htf_zone.md` + reviewer.

---

## Fuera de alcance (#20)

- Prefetch/reorden OB (#21).
- Endurecer umbrales PLAN MAESTRO (#19) — pero usar `STRAT_A_MIN_PAYOUT` para HTF library si #19 ya merged.
- Refactor completo a `entry_decision_engine` como único gate.
- Validación demo (#22).
- Cambios en `zone_memory.py` scoring rules.

---

## Notas para `spec_author`

- Decidir: **¿veto muro zone_memory (-10) obligatorio o solo scoring?** ROADMAP y `entry_decision_engine` sugieren veto; `feature_list` solo exige población + HTF bloqueo.
- Decidir: **grace period HTF** al arranque (recomendado 120–180s o rechazo estricto).
- Decidir: si `_score_trend` migra 100% a 15m o solo veto duro + score 5m (ROADMAP pide ambos).
- No editar `feature_list.json` hasta fase implementer/reviewer.