# Design — strat_a_test_suite

> Feature id=18. Fase SA-2 — cobertura de tests STRAT-A.
> Referencias: `docs/architecture.md` (tests sin broker),
> `docs/conventions.md` (un archivo de test por módulo),
> `specs/strat_a_evaluate/` (baseline unitarios #17),
> `tests/test_scanner.py` (patrones de mock existentes).

---

## Objetivo

Completar la **suite de tests STRAT-A** sin alterar la lógica de producción.
Prioridad: tests puros y mocks de I/O. Meta de conteo: **≥25 tests STRAT-A**
en total (15 unitarios existentes + ≥10 nuevos en E2E/pending/executor).

---

## Gap analysis (estado actual vs SA-2)

| Área | Estado actual | Acción en #18 |
|------|---------------|---------------|
| `evaluate_strat_a` rebote/ruptura/zona joven/blacklist/hint | ✅ 10 tests en `test_strat_a.py` | Mantener; añadir R9 (engulfing explícito) |
| Patrones 1m hammer/shooting_star | ✅ implícitos en rebote ceiling/floor | Añadir test engulfing CALL explícito (R9) |
| `pending_reversals` confirmación | ✅ 1 regresión en `test_scanner.py` | Migrar lógica a `test_scanner_strat_a.py`; ampliar wait/expire/cancel (R11–R14) |
| E2E scanner→candidato→score | ❌ | Nuevo archivo ≥5 casos (R2, R15–R16) |
| Executor `strategy_origin` / `stage` | ❌ | 2 tests en `test_executor.py` (R17–R18) |
| Trazabilidad | ❌ | `progress/impl_strat_a_test_suite.md` (R20) |

---

## Archivos a crear / modificar

| Archivo | Cambio |
|---------|--------|
| `tests/test_scanner_strat_a.py` | **Nuevo** — E2E STRAT-A + pending reversals (≥8 tests objetivo) |
| `tests/test_strat_a.py` | **+1 test** — `bullish_engulfing` CALL rebote (R9); mantener ≥15 total |
| `tests/test_executor.py` | **+2 tests** — `strategy_origin` + `stage` initial/breakout (R17–R18) |
| `progress/impl_strat_a_test_suite.md` | Mapa trazabilidad R→test (implementer) |

**Sin cambios en `src/`** salvo que el reviewer detecte un hook mínimo
indispensable (no anticipado en este diseño).

**Sin mover** tests de `test_scanner.py` que no son STRAT-A; el test de
confirmación pending puede **permanecer** como regresión (R19) mientras los
nuevos escenarios viven en `test_scanner_strat_a.py`.

---

## tests/test_scanner_strat_a.py — estructura

### Fixtures locales (duplicar patrón de `test_scanner.py`)

```python
class FakeBot: ...          # copia mínima: pending_reversals, zones, stats, dry_run
def _candle(ts, price): ...
def _make_strat_a_scanner(monkeypatch, assets) -> tuple[FakeBot, MagicMock, AssetScanner]
def _consolidation_candles_5m(ceiling, floor, n=15) -> list[Candle]
def _rebound_ceiling_last_bar(ceiling) -> Candle
def _valid_put_rejection_1m() -> list[Candle]
```

No extraer a `conftest.py` en esta feature (evita alcance transversal); duplicar
helpers necesarios mantiene homogeneidad con `test_scanner.py`.

### Mocks obligatorios

| Dependencia | Mock |
|-------------|------|
| `scanner.get_open_assets` | `AsyncMock(return_value=[("EURUSD_otc", 85)])` |
| `scanner.fetch_candles_with_retry` | Velas sintéticas por TF (300/60/900/10800) |
| `scan_prefetch.fetch_candles_with_retry` | Mismo fake_fetch |
| `scanner.detect_reversal_pattern` | `CandleSignal` controlado por escenario |
| `scanner._process_pending_martin` | `AsyncMock(return_value=([], False))` |
| `executor._compute_initial_amount` | `(1.0, 0.8)` |
| `executor._update_dynamic_threshold` | Umbral fijo (p. ej. 65) para R16 |
| `executor.enter_trade` | `AsyncMock` en tests de selección (R16) |
| `trade_journal.get_journal` | Mock con `_conn=None` o SQLite en memoria |

### Tests E2E planificados (≥5, cubren R2 y R15–R16)

| Test propuesto | Cubre |
|----------------|-------|
| `test_strat_a_e2e_rebound_ceiling_produces_scored_candidate` | R15 — candidato PUT, score>0, `_entry_mode=rebound_ceiling` |
| `test_strat_a_e2e_breakout_above_sets_stage_breakout` | R15 — `_stage=breakout`, `_entry_mode=breakout_above` |
| `test_strat_a_e2e_young_zone_skips_candidate` | R6/R15 — sin candidato; `stats["rejected_young_zone"]` incrementado |
| `test_strat_a_e2e_pending_hint_enqueues_reversal` | R10 — `bot.pending_reversals` poblado tras evaluate |
| `test_strat_a_e2e_select_best_only_above_threshold` | R16 — `enter_trade` llamado solo para score≥umbral |
| `test_strat_a_e2e_breakout_below_produces_put_candidate` | R5/R15 — ruptura bajista (opcional sexto caso) |

**Punto de entrada E2E:** invocar `_scan_phase_evaluate_assets(ScanCycleData)` con
`ScanCycleData` precargado (patrón de `test_scanner.py::test_strat_a_only_skips_momentum_candidate`).
Para R16, encadenar `_scan_phase_select_execute(eval_result, assets)` con
candidatos fabricados o salida real del paso anterior.

### Tests pending_reversals planificados (R11–R14)

| Test propuesto | Cubre |
|----------------|-------|
| `test_pending_reversal_active_wait_increments_scans_waited` | R11 |
| `test_pending_reversal_confirmed_returns_candidate_and_clears` | R12 |
| `test_pending_reversal_expires_after_max_wait_scans` | R13 |
| `test_pending_reversal_cancelled_when_price_leaves_extreme` | R14 |

**Datos clave:** `PendingReversal(max_wait_scans=3)`; para R14 usar
`current_prices[sym]` fuera de tolerancia `price_at_ceiling`/`price_at_floor`.

---

## tests/test_strat_a.py — adición mínima

Un test nuevo para R9:

```python
def test_evaluate_strat_a_bullish_engulfing_call_rebound():
    # Rebote piso + CandleSignal("bullish_engulfing", 0.75, True)
    # assert has_signal, direction=="call", confirms True
```

Los tests existentes cubren R3–R8 sin duplicar:

| Requirement | Test existente |
|-------------|----------------|
| R3 | `test_evaluate_strat_a_rebound_ceiling_put` |
| R4 | `test_evaluate_strat_a_rebound_floor_call` |
| R5 | `test_evaluate_strat_a_breakout_above_with_volume`, `..._below_with_volume` |
| R6 | `test_evaluate_strat_a_rejects_young_zone_rebound` |
| R7 | `test_evaluate_strat_a_put_pattern_blacklisted_emits_pending_hint` |
| R8 | `test_evaluate_strat_a_rejection_candle_emits_pending_hint` |

---

## tests/test_executor.py — integración

Dos tests async con patrón de `test_executor_dry_run_order`:

```python
async def test_executor_enter_trade_strat_a_initial_sets_origin_and_monitor(monkeypatch):
    # enter_trade(..., stage="initial", strategy_origin="STRAT-A")
    # assert bot.trades[sym].strategy_origin == "STRAT-A"
    # assert bot.trades[sym].stage == "initial"
    # assert bot.stats["strat_a_signals"] == 1
    # assert _monitor_trade_live task tracked (mock _track_task o spy create_task)

async def test_executor_enter_trade_strat_a_breakout_no_monitor(monkeypatch):
    # enter_trade(..., stage="breakout", strategy_origin="STRAT-A")
    # assert stage == "breakout"
    # assert ninguna tarea monitor:{sym} en bot._trade_tasks
```

Monkeypatch: `place_order`, `_sync_to_next_candle_open`, `_resolve_trade_after_expiry`,
`_monitor_trade_live` (AsyncMock), Massaniello `can_enter=True`.

---

## Construcción de velas sintéticas (E2E)

Para que `detect_consolidation` + `evaluate_strat_a` produzcan señal en E2E:

1. **15+ velas 5m** con rango estrecho (`range_pct` < `max_range_pct`).
2. **Última vela** en techo (`close ≈ ceiling`) o ruptura (`broke_above` con cuerpo voluminoso).
3. **3 velas 1m** que pasen `validate_rejection_candle` para la dirección.
4. **Zona madura:** `detected_at` ≥ `ZONE_AGE_REBOUND_MIN` minutos atrás.
5. **H1/OB/MA:** listas vacías o neutras; mocks devuelven `[]` sin error.

Para ruptura E2E, historial con volumen relativo alto en la vela de ruptura
(replicar ratios de `test_evaluate_strat_a_breakout_above_with_volume`).

---

## Alternativa descartada

**Refactorizar `scanner.py` para inyectar `evaluate_strat_a` como dependencia**
solo para tests. Rechazada porque:

- Viola el principio de no tocar `src/` en una feature de tests.
- Los mocks de módulo (`monkeypatch.setattr("scanner.evaluate_strat_a", ...)`) ya
  permiten aislar fases sin hooks de producción.
- El patrón establecido en `test_scanner.py` usa `ScanCycleData` precargado sin
  modificar el scanner.

---

## Alternativa descartada (archivo E2E)

**Ampliar solo `tests/test_scanner.py`** en lugar de crear `test_scanner_strat_a.py`.
Rechazada porque:

- `docs/conventions.md` prescribe un archivo por módulo/área; STRAT-A E2E
  concentraría ≥8 escenarios y diluiría tests genéricos del scanner.
- El `acceptance` de #18 nombra explícitamente `test_scanner_strat_a.py`.
- Facilita trazabilidad SA-2 en el reviewer.

---

## Fuera de alcance (#18)

- Endurecer umbrales PLAN MAESTRO (#19).
- Tests de `strat_a_radar.py` (feature separada; 3 tests ya existen).
- Tests con conexión real a Quotex.
- Backtesting offline (#9).
- Cambios en `_process_pending_reversals` para reutilizar `evaluate_strat_a`.

---

## Verificación

1. `python -m pytest tests/test_strat_a.py tests/test_scanner_strat_a.py tests/test_executor.py -v`
2. `python -m pytest tests/ -v` (regresión completa, R19)
3. `.\init.ps1` (R21)
4. Conteo: `test_strat_a.py` ≥16, `test_scanner_strat_a.py` ≥5, total STRAT-A ≥25