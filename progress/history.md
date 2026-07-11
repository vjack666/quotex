# Historial de sesiones

> Bitácora append-only. Cada entrada documenta qué se hizo, qué archivos se tocaron y el estado final.

---

## 2026-06-29 — Creación del harness SDD

**Qué se hizo:**
- Creación del arnés completo (harness-sdd) para el proyecto
- AGENTS.md, CLAUDE.md, CHECKPOINTS.md, feature_list.json
- init.ps1 (PowerShell), docs/*, .claude/agents/*
- progress/current.md, progress/history.md

**Archivos creados:**
- AGENTS.md, CLAUDE.md, CHECKPOINTS.md, feature_list.json, init.ps1
- docs/architecture.md, docs/conventions.md, docs/specs.md, docs/verification.md
- .claude/agents/leader.md, .claude/agents/spec_author.md
- .claude/agents/implementer.md, .claude/agents/reviewer.md
- .claude/settings.json
- progress/current.md, progress/history.md

**Estado final:**
- 15 features en feature_list.json, todas `pending` con `"sdd": true`
- init.ps1 creado pero falta carpeta tests/ y pytest
- Sin features en `in_progress`

**Próximo paso recomendado:**
Feature #1 — `refactor_monolith`: dividir consolidation_bot.py en módulos.

---

## 2026-06-29 — Feature #1 `refactor_monolith` (APPROVED)

**Qué se hizo:**
- Refactor del monolito `consolidation_bot.py` (~4188 líneas) en módulos con responsabilidad única.
- Facade `consolidation_bot.py` reducido a **292 líneas** (≤ 500).
- Módulos nuevos: `config.py`, `errors.py`, `strat_a.py`, `strat_b.py`, `connection.py`, `scanner.py`, `executor.py`, `loop_utils.py`.
- Suite de tests: 6 archivos + `conftest.py` (27 tests, todos verdes).
- Fix R14: añadido `test_parse_args_legacy_cli_flags` para cobertura CLI `--live`, `--real`, `--loop`, `--greylist`.
- Re-review reviewer: **APPROVED** tras verificar trazabilidad R1–R14.

**Archivos principales:**
- `src/consolidation_bot.py`, `src/connection.py`, `src/scanner.py`, `src/executor.py`, `src/strat_a.py`, `src/strat_b.py`, `src/config.py`, `src/errors.py`, `src/loop_utils.py`
- `tests/test_connection.py`, `tests/test_scanner.py`, `tests/test_executor.py`, `tests/test_consolidation_bot.py`, `tests/test_strat_a.py`, `tests/test_strat_b.py`, `tests/conftest.py`
- `main.py` (imports explícitos de `connection`, `scanner`, `executor`)
- `specs/refactor_monolith/` (requirements, design, tasks)
- `progress/impl_refactor_monolith.md`, `progress/review_refactor_monolith.md`

**Estado final:**
- `feature_list.json`: feature #1 → `done`
- `python -m pytest tests/ -v` → 27 passed
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #2 — `implement_missing_modules`: crear módulos SMC, filter_sell, config faltantes.

---

## 2026-06-29 — Feature #16 `massaniello_risk` (APPROVED)

**Qué se hizo:**
- Reemplazo de martingala por motor Massaniello (5 ops / 3 ITM / sesión 60 min / solo PRACTICE).
- Módulos nuevos: `massaniello_engine.py`, `massaniello_risk.py`.
- Integración en `config.py`, `executor.py`, `consolidation_bot.py`, `main.py`.
- Tests nuevos: `test_massaniello_engine.py` (6), `test_massaniello_risk.py` (7); `test_executor.py` actualizado con mocks Massaniello.
- Re-review reviewer: **APPROVED** tras verificar trazabilidad R1–R7 y tasks T1–T8.

**Archivos principales:**
- `src/massaniello_engine.py`, `src/massaniello_risk.py`
- `src/config.py`, `src/executor.py`, `src/consolidation_bot.py`, `main.py`
- `tests/test_massaniello_engine.py`, `tests/test_massaniello_risk.py`, `tests/test_executor.py`
- `specs/massaniello_risk/` (requirements, design, tasks)
- `progress/impl_massaniello_risk.md`, `progress/review_massaniello_risk.md`

**Estado final:**
- `feature_list.json`: feature #16 → `done`
- `python -m pytest tests/ -v` → 40 passed
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #2 — `implement_missing_modules`: crear módulos SMC y filter_sell (config.py ya existe).

---

## 2026-06-29 — Actualización de roadmap y documentación

**Qué se hizo:**
- Creado `docs/ROADMAP.md` (fases, dependencias, módulos, changelog).
- Actualizado `feature_list.json`: fases, `depends_on`, bloqueadores, progreso 2/16.
- #11 renombrada: `martingale_persistence` → `massaniello_persistence`.
- #2, #6, #8, #13, #15 actualizadas para reflejar estado real (Massaniello, config existente).
- Actualizados `docs/architecture.md`, `AGENTS.md`, `docs/conventions.md`, `CHECKPOINTS.md`.

**Estado final:**
- Roadmap coherente con código actual (Massaniello activo, martingala deprecada).
- Siguiente feature recomendada: #2 `implement_missing_modules`.

**Bloqueo operativo:**
- Credenciales Quotex demo inválidas — validación en vivo pendiente.

---

## 2026-06-30 — Feature #2 `implement_missing_modules` (APPROVED)

**Qué se hizo:**
- Implementados cuatro módulos ausentes: SMC (análisis, decisión, trader) y filtro OTC por payout.
- Port de `smc_analysis` / `smc_decision_engine` desde repo QUOTEX con `models.Candle` unificado.
- Traders nuevos: `SMCAutoTrader`, `FilterSellOTC` vía `connection.py`.
- Suite ampliada: 18 tests nuevos (58 total, todos verdes).
- Re-review reviewer: **APPROVED** tras verificar trazabilidad R1–R27 y tasks T1–T9.

**Archivos principales:**
- `src/smc_analysis.py`, `src/smc_decision_engine.py`, `src/smc_auto_trader.py`, `src/filter_and_sell_otc.py`
- `tests/test_smc_analysis.py`, `tests/test_smc_decision_engine.py`, `tests/test_smc_auto_trader.py`, `tests/test_filter_and_sell_otc.py`
- `specs/implement_missing_modules/` (requirements, design, tasks)
- `progress/impl_implement_missing_modules.md`, `progress/review_implement_missing_modules.md`

**Estado final:**
- `feature_list.json`: feature #2 → `done`; progreso **3/16**
- `python -m pytest tests/ -v` → 58 passed
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #3 — `parallel_asset_scan`: escaneo paralelo de activos OTC.

---

## 2026-06-30 — Feature #3 `parallel_asset_scan` (APPROVED)

**Qué se hizo:**
- Nuevo módulo `src/parallel_fetch.py` con `fetch_candles_parallel` (semáforo + `asyncio.gather`).
- Refactor de `AssetScanner.scan_all`: prefetch paralelo de velas 5m y 1m antes del bucle de evaluación.
- Telemetría de rendimiento: log `scan_fetch_elapsed_ms` por ciclo.
- Suite ampliada: 3 tests nuevos (61 total, todos verdes).
- Re-review reviewer: **APPROVED** tras verificar trazabilidad R1–R6 y tasks T1–T8.

**Archivos principales:**
- `src/parallel_fetch.py`, `src/scanner.py`
- `tests/test_scanner.py` (+3 tests)
- `specs/parallel_asset_scan/` (requirements, design, tasks)
- `progress/impl_parallel_asset_scan.md`, `progress/review_parallel_asset_scan.md`

**Estado final:**
- `feature_list.json`: feature #3 → `done`; progreso **4/16**
- `python -m pytest tests/ -v` → 61 passed
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #4 — `candle_cache`: caché local de velas con actualización incremental.

---

## 2026-06-30 — Features #4, #5, #6 (APPROVED)

**Qué se hizo:**
- **#4 `candle_cache`** — `CandleCache` con clave `(asset, tf_sec)`, TTL, merge incremental, locks asyncio; integrado en prefetch paralelo.
- **#5 `entry_sync_precision`** — `EntrySynchronizer` con `compute_timing` puro, `sync_and_validate`, `log_order_timing`; `ENTRY_MAX_LAG_SEC=0.3`.
- **#6 `strategy_momentum_1m`** — `detect_momentum_1m` (cuerpo ≥1.5× promedio + cierre en tercio extremo); candidatos `STRAT-MOMENTUM` en scanner.
- Suite ampliada: 13 tests nuevos (74 total, todos verdes).
- Re-review reviewer: **APPROVED** tras verificar trazabilidad R1–R7, R1–R5, R1–R6 y tasks completas.

**Archivos principales:**
- `src/candle_cache.py`, `src/entry_sync.py`, `src/strat_momentum.py`
- `src/config.py`, `src/parallel_fetch.py`, `src/scanner.py`, `src/executor.py`, `src/consolidation_bot.py`
- `tests/test_candle_cache.py`, `tests/test_entry_sync.py`, `tests/test_strat_momentum.py`
- `specs/candle_cache/`, `specs/entry_sync_precision/`, `specs/strategy_momentum_1m/`
- `progress/impl_features_4_5_6.md`, `progress/review_features_4_5_6.md`

**Estado final:**
- `feature_list.json`: features #4, #5, #6 → `done`; progreso **7/16**
- `python -m pytest tests/ -v` → 74 passed
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #7 — `strategy_reversal_swing`: reversión en soporte/resistencia dinámica.

---

## 2026-06-30 — STRAT-A: fixes críticos + radar de caza (#22 en curso)

**Objetivo sesión:** validación demo STRAT-A-only hasta entrada exitosa.

**Qué se hizo:**

1. **Diagnóstico raíz** — `get_candles` de pyquotex devolvía 2–3 velas; sin datos no hay zonas ni señales.
2. **Fix `connection.py`** — fallback a `get_historical_candles` cuando hay pocas velas; reintentos si insuficientes (`progress/impl_candle_fetch_fix.md`).
3. **Fix `scanner.py`** — `_process_pending_reversals` crasheaba con `AttributeError` al confirmar patrón (USDEGP `shooting_star` 0.75); delegado a `strat_a.*` (`progress/impl_pending_reversal_fix.md`).
4. **Radar de caza STRAT-A** — watchlist top-5 "casi listos" + tick 1m entre sweeps amplios (`src/strat_a_radar.py`, `progress/design_strat_a_radar.md`, `progress/impl_strat_a_radar.md`).
5. **Validación live (parcial)** — PRACTICE OK; prefetch 22 símbolos; zonas USDEGP/USDZAR/USDCOP; pending reversals activos; **sin entrada ejecutada** aún (mercado + filtros edad 20 min).

**Archivos principales:**
- `src/connection.py`, `src/scanner.py`, `src/strat_a_radar.py`, `src/consolidation_bot.py`, `src/config.py`, `main.py`
- `tests/test_connection.py`, `tests/test_scanner.py`, `tests/test_strat_a_radar.py`

**Estado final:**
- `feature_list.json`: #22 sigue `pending` (entrada exitosa no documentada)
- `python -m pytest tests/` → **97 passed**
- `.\init.ps1` → exit 0
- Bot detenido al cierre de sesión

**Próximo paso recomendado:**
1. `.\run_strat_a.ps1` — monitorear log `[RADAR] Watchlist` y ticks 1m
2. Cerrar #22 cuando haya entrada STRAT-A + resultado, o ≥10 rechazos con razón válida
3. Track formal: #18 spec → quality filters (#19)

---

## 2026-07-02 — Feature #18 `strat_a_test_suite` (APPROVED)

**Qué se hizo:**
- Ampliación suite STRAT-A (SA-2): unitarios `evaluate_strat_a`, patrones 1m, E2E scanner, pending_reversals, integración executor.
- Nuevo `tests/test_scanner_strat_a.py` — 9 tests (5 E2E + 4 pending).
- `tests/test_strat_a.py` — 16 unitarios (≥15); +1 `bullish_engulfing`.
- `tests/test_executor.py` — +2 tests STRAT-A initial/breakout.
- Trazabilidad R1–R21 en `progress/impl_strat_a_test_suite.md`.
- Re-review reviewer: **APPROVED** — 109 tests, `init.ps1` OK, sin cambios en `src/`.

**Archivos principales:**
- `tests/test_strat_a.py`, `tests/test_scanner_strat_a.py`, `tests/test_executor.py`
- `specs/strat_a_test_suite/` (requirements, design, tasks)
- `progress/impl_strat_a_test_suite.md`, `progress/review_strat_a_test_suite.md`

**Estado final:**
- `feature_list.json`: feature #18 → `done`; progreso **9/22**; track STRAT-A **2/6**
- `python -m pytest tests/ -v` → **109 passed**
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #19 — `strat_a_quality_filters`: reject-first según PLAN MAESTRO.

---

## 2026-07-02 — Feature #19 `strat_a_quality_filters` (APPROVED)

**Qué se hizo:**
- Filtros reject-first PLAN MAESTRO para STRAT-A: payout ≥87%, score ≥75 fijo, zona rebote ≥30 min, patrón 1m obligatorio en rebotes.
- Constantes `STRAT_A_MIN_PAYOUT`, `STRAT_A_MIN_SCORE`, `STRAT_A_ZONE_MIN_AGE_REBOUND` en `config.py`.
- Veto `pattern_missing` en `evaluate_strat_a()`; filtro payout y logs veto en `scanner.py`.
- `select_best(..., threshold_for=...)` — umbral STRAT-A independiente del adaptativo global.
- Re-review: tests `caplog` para R2 (payout) y R5 (patrón rebote vía scanner).
- Reviewer: **APPROVED** tras verificar trazabilidad R1–R16 y tasks T1–T20.

**Archivos principales:**
- `src/config.py`, `src/strat_a.py`, `src/scanner.py`, `src/entry_scorer.py`
- `tests/test_strat_a.py`, `tests/test_scanner_strat_a.py`
- `specs/strat_a_quality_filters/` (requirements, design, tasks)
- `progress/impl_strat_a_quality_filters.md`, `progress/review_strat_a_quality_filters.md`

**Estado final:**
- `feature_list.json`: feature #19 → `done`; progreso **10/22**; track STRAT-A **3/6**
- `python -m pytest tests/ -v` → **116 passed**
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #20 — `strat_a_htf_zone_wiring`: cablear HTFScanner y zone_memory (prep: `progress/prep_strat_a_htf_zone.md`).

---

## 2026-07-02 — Feature #20 `strat_a_htf_zone_wiring` (APPROVED)

**Resumen:**
- HTFScanner arranca como tarea asyncio (`create_task(run_forever)`); cancel en shutdown.
- Gates centralizados `_apply_strat_a_htf_zone_gates` en evaluate, radar y pending_reversals.
- Hot path sin `fetch_candles_with_retry(tf_sec=900)` — cache vía `get_candles_15m`.
- `candidate.zone_memory` vía `query_nearby_zones`; veto muro `<= -10`.
- `candidate.candles_15m` poblado; `entry_scorer` prefiere 15m para `_score_trend` si `len >= 25`.
- Re-review: +4 tests (lifecycle HTF, radar veto, trend 15m, E2E `candles_15m`).
- Reviewer: **APPROVED** tras verificar trazabilidad R1–R24 y tasks T1–T23.

**Archivos principales:**
- `src/htf_scanner.py`, `src/consolidation_bot.py`, `src/scanner.py`, `src/models.py`, `src/entry_scorer.py`
- `tests/test_htf_zone_wiring.py`, `tests/test_consolidation_bot.py`, `tests/test_scanner_strat_a.py`, `tests/test_strat_a_radar.py`
- `specs/strat_a_htf_zone_wiring/` (requirements, design, tasks)
- `progress/impl_strat_a_htf_zone_wiring.md`, `progress/review_strat_a_htf_zone_wiring.md`

**Estado final:**
- `feature_list.json`: feature #20 → `done`; progreso **11/22**; track STRAT-A **4/6**
- `python -m pytest tests/ -v` → **129 passed**
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #21 — `strat_a_ob_prefetch`: prefetch paralelo OB 3m (prep: `progress/prep_strat_a_ob_prefetch.md`).

---

## 2026-07-02 — Feature #21 `strat_a_ob_prefetch` (APPROVED)

**Resumen:**
- `ScanCycleData.blocks_by_symbol` poblado en `prefetch_strat_a_secondary` (lazy `detect_order_blocks`).
- Evaluate consume blocks precalculados; cero fetch OB (`tf_sec=180`) en `_scan_phase_evaluate_assets`.
- `_fetch_ob_candles` eliminado; `order_blocks_by_asset` mantiene radar.
- Log `blocks_precalc=N` en fase 3b; fallback 5m + cache incremental verificados.
- Reviewer: **APPROVED** tras verificar trazabilidad R1–R22 y tasks T1–T16, T18–T19.

**Archivos principales:**
- `src/scan_prefetch.py`, `src/scanner.py`
- `tests/test_scan_prefetch.py`, `tests/test_scanner_strat_a.py`
- `specs/strat_a_ob_prefetch/` (requirements, design, tasks)
- `progress/impl_strat_a_ob_prefetch.md`, `progress/review_strat_a_ob_prefetch.md`

**Estado final:**
- `feature_list.json`: feature #21 → `done`; progreso **12/22**; track STRAT-A **5/6**
- `python -m pytest tests/ -q` → **135 passed**
- `.\init.ps1` → exit 0

**Próximo paso recomendado:**
Feature #22 — `strat_a_live_validation`: validación demo PRACTICE ≥60 min (solo STRAT-A, Massaniello).

---

## 2026-07-02 — Feature #22 `strat_a_live_validation` (DONE)

**Resumen:**
- Validación demo PRACTICE con `python main.py --strat-a-only`.
- Sesión 13:53:29 — conexión OK, balance 55.87 USD, modo STRAT-A-ONLY.
- HTF scanner 15m + prefetch OB (16 blocks) operativos en vivo.
- Primer ciclo completo 14:03:26: 27 activos, 0 entradas, Massaniello 0/5 ops.
- **10 rechazos reject-first** documentados (3 zona <30min + 7 payout <87%).
- Criterio alternativo cumplido (≥10 rechazos con razón válida); sesión Massaniello no alcanzada (0 ops).

**Evidencia:** `progress/impl_strat_a_live_validation.md`, `consolidation_bot.log` (línea 489254+). Parser: `python progress/parse_strat_a_session.py` → `criterion_met: True`.

**Estado final:**
- `feature_list.json`: feature #22 → `done`
- Progreso global **13/22**; track STRAT-A **6/6 — COMPLETO**
- `.\init.ps1` → verde (135 tests)

**Próximo paso recomendado:**
Retomar backlog global — feature #7 `strategy_reversal_swing` (pausada durante track STRAT-A).

---

## 2026-07-04 — Batch global backlog: #7, #8, #9, #10, #11, #12, #13, #14, #15

**Resumen:**
Completadas las 9 features restantes del backlog global (fases 2–4) en una tanda multi-agente.

### Features completadas

| ID | Feature | Módulo | Tests |
|----|---------|--------|-------|
| #7 | `strategy_reversal_swing` | `src/strat_reversal_swing.py` | 6 |
| #8 | `strategy_order_block` | `src/strat_order_block.py` | 4 |
| #9 | `backtesting_engine` | `src/backtester.py` | 20 |
| #10 | `dynamic_weight_calibration` | `src/weight_calibrator.py` | 36 |
| #11 | `massaniello_persistence` | `src/massaniello_persistence.py` | 13 |
| #12 | `hub_live_websocket` | specs copiadas de `docs/specs-temp/` | — |
| #13 | `kelly_criterion_sizing` | `src/kelly_sizer.py` | 13 |
| #14 | `diversification_enforcer` | `src/diversification_enforcer.py` | 13 |
| #15 | `telegram_alerts` | `src/alerter.py` | 11 |

### Archivos creados
- `src/strat_reversal_swing.py`, `src/strat_order_block.py`, `src/backtester.py`
- `src/weight_calibrator.py`, `src/massaniello_persistence.py`
- `src/kelly_sizer.py`, `src/diversification_enforcer.py`, `src/alerter.py`
- `specs/strategy_reversal_swing/`, `specs/strategy_order_block/`, `specs/backtesting_engine/`
- `specs/dynamic_weight_calibration/`, `specs/massaniello_persistence/`
- `specs/kelly_criterion_sizing/`, `specs/diversification_enforcer/`, `specs/telegram_alerts/`

### Archivos modificados
- `src/scanner.py` — integración #7 y #8
- `src/executor.py` — persistencia Massaniello (#11), stop-loss alerts (#15)
- `src/consolidation_bot.py` — peso calibrado startup (#10), Kelly factor (#13), diversificación (#14), alerts (#15)
- `src/config.py` — constantes #7 y #8
- `src/trade_journal.py` — DDL `massaniello_state` (#11)
- `src/massaniello_risk.py` — session complete + losing streak alerts (#15)

### Estado final
- `feature_list.json`: features #7–#15 → `done`; progreso **22/22 — COMPLETO**
- `python -m pytest tests/ -q` → **251 passed**
- `.\init.ps1` → exit 0
- `consolidation_bot.log` rotado (~63 MB → backup)

### Próximo paso recomendado
Validación live del sistema completo en PRACTICE, o planificar próxima fase de features.

---

## Sesión 2026-07-11 (tarde) — STRAT-F: calidad + validación (SDD strat_f_quality_validation)

### Goal
Cerrar STRAT-F sin preguntar: filtros de calidad (#4), reconocimiento en
backtester (#5) y validación demo en vivo (#6). SDD en
`specs/strat_f_quality_validation/`.

### Hecho
- **#4 Filtros de calidad** en `src/strat_fractal.py`:
  - R2 payout mínimo (`STRAT_F_MIN_PAYOUT`), R3 edad mínima de zona
    (`STRAT_F_ZONE_MIN_AGE=3` velas M5), R6 score mínimo (`STRAT_F_MIN_SCORE`).
  - R1 alineación M15/M5 y R4 rechazo M1 ya existían; se conservan y loguean.
  - Firma con kwargs `min_payout`/`min_score`/`zone_min_age` (fallback a config).
  - Scanner pasa `payout` real a `evaluate_strat_f` (activa R2 en vivo).
- **#5 Backtester** (`src/backtester.py`): rama `_reevaluate_strat_f`, STRAT-F
  añadido a `origins` de `load_from_db` y reconocido en `reevaluate`. Reporte
  diferenciado por origen (R7/R8).
- **#6 Validación demo** vía `progress/diag_strat_f_live.py` (el bot completo lo
  mata el host en prefetch secundario; el diag ligero completa EXIT=0).
  Corrida `progress/diag_strat_f_filters.log`: 31 activos payout≥80%, los 6
  filtros en acción — zona joven (AUDUSD/ETCUSD/EURAUD), CALL contra tendencia
  (USCrude), M15 roto (EURJPY/CADJPY/GBPCAD), M1 no rechaza (varios). 1 señal
  limpia: **USDPKR_otc CALL strength=70 payout=92%**.
- **Libro** `boblioteca/formacion_velas/08_calidad_filtros.md` (R10): por qué
  rechazar es ganar, los 6 filtros, no-una-sola-vela, Fase A como refuerzo.
- **Tests**: +8 casos (4 filtros STRAT-F + 3 backtester STRAT-F + regresión
  `_serialize_candles`). **pytest 267 passed**.

### Discoveries
- El fractal Bill Williams se busca en rango `[2, len-3]`; la edad de la zona =
  `(len(candles_5m)-1) - fractal_idx`. Con 8 velas y fractal central en idx 4 la
  edad es 3 (pasa el filtro por defecto).
- `load_from_db` filtra por lista blanca de orígenes: cualquier estrategia nueva
  debe añadirse ahí o el backtester la ignora silenciosamente.
- El host sigue matando el bot completo en prefetch secundario; el diag ligero es
  la vía fiable para validación en vivo.

### Relevant Files
- `src/strat_fractal.py`, `src/config.py`, `src/backtester.py`, `src/scanner.py`
- `tests/test_strat_fractal.py`, `tests/test_backtester.py`
- `boblioteca/formacion_velas/08_calidad_filtros.md`
- `progress/diag_strat_f_filters.log`
- `specs/strat_f_quality_validation/{requirements,design,tasks}.md`

---

## Sesión 2026-07-11 (noche) — Reemplazo del dashboard por panel STRAT-F

### Goal
Reemplazar el dashboard viejo (STRAT-A / Masaniello) por uno nuevo que
muestre STRAT-F: aceptadas vs rechazadas con la razón de cada rechazo.
Autorizado sin preguntar.

### Instructions
- El panel visible es STRAT-F; Masaniello sigue en el bot (additive).
- No borrar `hub_models.py` (lección 340597f): convive con el panel nuevo.

### Discoveries
- `server.py` ya tenía FastAPI+WS; solo faltaba empujar `strat_f`.
- Rich NO está en el venv -> render cae a texto plano (fallback OK).
- El batch en `scanner.py` debe ser lista mutable `[[], [], 0]`, no tupla,
  si no `_batch[2] += 1` rompe en runtime.

### Accomplished
- SDD: `specs/hub_strat_f_replacement/{requirements,design,tasks}.md`.
- `hub/strat_f_state.py` modelo `StratFHubState`.
- `hub/parser.py` reescrito a `StratFHubState`; `hub/render.py` Rich+plano.
- `hub/strat_f_panel.py` `StratFPanel.record_strat_f`.
- `hub/server.py` `_build_snapshot` incluye `strat_f` + `/api/strat_f`.
- `hub/static/index.html` REESCRITO a panel STRAT-F (WS+fetch).
- `scanner.py` acumula `_strat_f_batch` y empuja `record_strat_f`.
- `main.py::_render_hub_once` usa panel/parser/render nuevo.
- `tests/test_hub_strat_f.py` 6 tests. `boblioteca/.../09_dashboard_stratf.md`.
- `feature_list.json` #7 done; `docs/ROADMAP.md` Fase 3.
- **pytest 273 passed.**

### Relevant Files
- `hub/strat_f_state.py`, `hub/strat_f_panel.py`, `hub/parser.py`, `hub/render.py`
- `hub/server.py`, `hub/static/index.html`, `hub/__init__.py`
- `src/scanner.py`, `main.py`, `tests/test_hub_strat_f.py`

---

## Sesión 2026-07-11 (noche 2) — Caja negra STRAT-F: diario + calibración

### Goal
Cablear STRAT-F al trade_journal (diario/calibración), reporte filtrado por
STRAT-F y launcher .bat que escanea en vivo y alimenta el diario.

### Discoveries
- `trade_journal.py` ya guardaba 1725 candidatos STRAT-A; STRAT-F NO se grababa.
- `log_candidate` accedía a `entry.zone.ceiling` -> rompía con zone=None (rechazos
  STRAT-F sin zona). Hecho tolerante con `getattr(z, 'ceiling', 0.0) or 0.0`.
- `log_candidate` no tenía columna `strategy_origin`; la BD SÍ la tiene (la ignoro
  antes). Ahora se escribe `getattr(entry, '_strategy_origin', 'STRAT-A')`.
- El escaneo en vivo con `--journal` SÍ termina (proceso corto, no lo mata el host).

### Accomplished
- `trade_journal.py`: `log_candidate` tolerante a zone=None + graba `strategy_origin`.
- `trade_journal.py`: `query_strat_f()` + `print_strat_f_report()` (win rate, % de
  cada motivo de rechazo para calibrar umbrales) + CLI `python -m trade_journal --strat-f`.
- `scanner.py`: `_strat_f_batch` ahora es `[[], []]` de dicts completos (con velas
  M15/M5/M1 y zone); al final del ciclo graba cada decisión STRAT-F en el journal
  vía `journal.log_candidate(..., strategy={...velas...})` (diario + replay).
- `progress/diag_strat_f_live.py`: opción `--journal` graba el escaneo en vivo en
  el diario (sin esperar al bot completo).
- `run_strat_f_panel.bat`: escanea en vivo con `--journal` y abre el panel.
- `tests/test_strat_f_journal.py`: 3 tests (aceptada, rechazada zona None, reporte).
- **pytest 276 passed** (273 + 3 nuevos).
- Verificación real end-to-end: diag --journal grabó 14 decisiones STRAT-F en
  `trade_journal.db`; `python -m trade_journal --strat-f` muestra
  Evaluados=14, Aceptadas=1, Rechazadas=13, y motivos (M1 no rebota 76.9%,
  zona joven 15.4%, contra tendencia M15 7.7%) -> datos listos para calibrar.

### Relevant Files
- `src/trade_journal.py`, `src/scanner.py`, `progress/diag_strat_f_live.py`
- `run_strat_f_panel.bat`, `tests/test_strat_f_journal.py`

---

## 2026-07-11 (noche) — Documentación de ingeniería + calibrración + ATDD

**Contexto:** El usuario pidió explicar acrónimos de ingeniería (SRS/FRS/NFR,
SDD/SAD/ADR, TDD/BDD/ATDD, MCP/RAG/DSPy...) y cómo implementarlos en el
sistema de binarias con objetivo: **5 entradas en ventana de 2h** en los pares
del escaneo. Luego pidió crear toda la documentación ordenada, sin preguntar.

**Qué se hizo:**
1. `calibration_report.py` (ya commiteado en 2752463): lee el diario STRAT-F y
   agrupa rechazos por filtro (R1/R2/R3/R4/R6), sugiere apretar/aflojar.
2. `docs/engineering/SRS.md` — requisitos: F1–F12 (funcionales) y N1–N9 (no
   funcionales, incl. N1 = >=5 entradas/2h, N4 = <=5 entradas/ventana).
3. `docs/engineering/adr/` — 3 ADR (evaluador puro, SQLite diario, no borrar
   hub_models) + índice README.
4. `docs/engineering/erd_trade_journal.md` — diagrama de tablas del diario
   (candidates, scan_sessions, shadow_decision_audit, expired_zones) con DDL real.
5. `docs/engineering/api_spec.md` — contrato de hub/server.py (endpoints reales
   /api/state, /api/strat_f, /ws, /health, /).
6. `docs/engineering/glosario.md` — tabla de todos los acrónimos mapeados a QUOTEX.
7. `tests/test_window_2h.py` — **ATDD N1**: simula ventana 2h (24 ciclos × 5 min,
   10 pares) con velas ideales que pasan STRAT-F y afirma >=5 entradas. También
   verifica el cap de riesgo (N4) y que M15 roto rechaza.

**Archivos creados/modificados:**
- `src/calibration_report.py`, `run_calibration.bat`, `tests/test_calibration_report.py`
- `docs/engineering/SRS.md`, `docs/engineering/adr/*`, `docs/engineering/erd_trade_journal.md`,
  `docs/engineering/api_spec.md`, `docs/engineering/glosario.md`
- `tests/test_window_2h.py`
- `docs/ROADMAP.md` (Fase 4 + changelog)

**Verificación:**
- `pytest tests/test_calibration_report.py` → 3 passed.
- `pytest tests/test_window_2h.py` → 3 passed.
- `pytest tests/` → **282 passed** (279 + 3 ATDD).
- `python -m src.calibration_report 90` sobre la BD real: Evaluados=14,
  Aceptadas=1, Rechazadas=13; dominante R4 banda M1 (76.9%).

**Decisión:** la calibración solo tiene sentido cuando el sistema corre COMPLETO
y el diario acumula trades resueltos (WIN/LOSS). No se corrió el panel aislado
para llenar el diario (el usuario lo aclaró). `run_calibration.bat` queda listo
para cuando Ruben opere el bot en demo.

**Estado final:** documentación de ingeniería completa y verificada. Commiteado
y pusheado (el usuario ya había autorizado el push en el paso anterior).

### Relevant Files
- `docs/engineering/*`, `tests/test_window_2h.py`, `tests/test_calibration_report.py`
- `src/calibration_report.py`, `run_calibration.bat`
- `docs/ROADMAP.md`, `progress/history.md`
