# Roadmap — quotex-hft-bot (post-Strategy B)

> **Fuente de verdad:** `feature_list.json`
> **Última actualización:** 2026-07-19
> **Changelog sesión:** `docs/CHANGELOG_2026-07-16.md`
> **Contexto:** Strategy B eliminada. **STRAT-F en producción** + stoch M15 help hard.
> Recolección **24/7** (Massaniello solo se resetea al fin de ciclo).

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Estrategias vivas | **STRAT-F** (foco), STRAT-A, MOMENTUM, REVERSAL_SWING, ORDER_BLOCK |
| STRAT-F | **✅ Operativa** (#1–#7) + **stoch help #9 done** |
| Place-order | **#10 smart_order_place done** |
| Strategy B | **ELIMINADA** (2026-07-11) |
| Gestión de riesgo | Massaniello 24/7 (reset al fin de ciclo; no para el bot) |
| Feature abierta en lista | #8 `schedule_auto` (pausado; cierre formal pendiente) |
| Siguiente valor en STRAT-F | Validar stoch hard en black box; opcional gate M1 micro-tendencia |
| Mejoras del resto del sistema | **Aplazadas** → `docs/BACKLOG_SYSTEM_IMPROVEMENTS.md` |

---

## Concepto de STRAT-F (une los libros de `boblioteca/`)

Marco fractal (la temporalidad mayor manda):
- **M15 (mayor / contexto)**: ¿el par está en rango Wyckoff o en tendencia?
  Si el rango está roto, no operamos rebotes.
- **M5 (media / estructura)**: fractal Bill Williams de 5 velas que cae en una
  banda naranja (zona Wyckoff) = evento de entrada.
- **M1 (menor / ejecución)**: vela que toca la banda y la rechaza (no cierra fuera).

Expiración 3 min (3 velas de M1). Alineación M15+M5+M1 sube la probabilidad.

---

## Roadmap por fases

### Fase 0 — Acomodar el scanner (base de STRAT-F)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 1 | `scanner_multi_tf_prefetch` | ✅ done | — |

### Fase 1 — STRAT-F (nueva estrategia)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 2 | `strat_f_baseline` | ✅ done | #1 |
| 3 | `strat_f_scanner_wiring` | ✅ done | #2 |
| 4 | `strat_f_filters` | ✅ done | #3 |

### Fase 2 — Validación
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 5 | `strat_f_backtest` | ✅ done | #3 |
| 6 | `strat_f_live_validation` | ✅ done | #4, #5 |

> **STRAT-F cerrado** (2026-07-11). SDD: `specs/strat_f_quality_validation/`.
> pytest 267 passed. Próxima fase a definir.

### Fase 3 — Dashboard STRAT-F (reemplazo del panel viejo)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 7 | `hub_strat_f_replacement` | ✅ done | #1, #2, #3, #4, #5, #6 |

> **Dashboard reemplazado** (2026-07-11). SDD: `specs/hub_strat_f_replacement/`.
> El panel ahora muestra aceptadas vs rechazadas STRAT-F con razón. pytest 273 passed.

### Fase 5 — Stoch help + ops 24/7 + place-order (2026-07-16/17)
| ID | Feature | Estado | Notas |
|----|---------|--------|-------|
| 9 | `stoch_entry_help` | ✅ done | Stoch M15 hard; `specs/stoch_entry_help/` |
| 10 | `smart_order_place` | ✅ done | Prewarm + hub last_order_attempt |
| — | Massaniello 24/7 | ✅ ad-hoc | Solo reset; no stop al fin de ciclo |
| — | Scan align 5m | ✅ ad-hoc | `ALIGN_SCAN_TO_CANDLE` + lead 0 |
| — | Quiet trade wait + log countdown | ✅ ad-hoc | Ver changelog |
| — | **Arranque inmediato** | ✅ ad-hoc | `consolidation_bot.py` escanea al conectar (sin despertador) |
| — | **Sin límite 60 min** | ✅ ad-hoc | `config.py SESSION_MAX_MIN=0`; Massaniello continuo |
| — | **Scan cada 1 min** | ✅ ad-hoc | `ALIGN_SCAN_TO_CANDLE=False`; cada 60s con countdown |
| 15 | **`parallel_scan_fase3`** | ✅ done (auditado+corregido 2026-07-17) | STRAT-F de FASE 3 en ProcessPool 10 workers (50% CPU); speedup 2.19x; STRAT-A intacto; dispatch vivificado + fix firma `upsert_young` |

> Detalle: `docs/CHANGELOG_2026-07-16.md`

### Fase 6 — Hub ops (abierto)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 8 | `schedule_auto` | ⏸ in_progress (paused) | — |

---

## Módulos afectados por STRAT-F

| Módulo | Cambio |
|--------|--------|
| `scan_prefetch.py` | bajar 15m → `ScanCycleData.candles_15m` (#1) |
| `src/strat_fractal.py` | **NUEVO** evaluador puro STRAT-F (#2) |
| `scanner.py` | cablear bloque STRAT-F (#3) |
| `config.py` | constantes `STRAT_F_*` (#3/#4) |
| `backtester.py` | reconocer origen `STRAT-F` (#5) |
| `tests/test_strat_fractal.py` | **NUEVO** (#2) |
| `hub/strat_f_state.py` | **NUEVO** modelo `StratFHubState` (#7) |
| `hub/strat_f_panel.py` | **NUEVO** capa visible STRAT-F (#7) |
| `hub/parser.py` | parsea log del diag a `StratFHubState` (#7) |
| `hub/render.py` | panel a color (Rich) aceptadas/rechazadas (#7) |
| `hub/server.py` | empuja `strat_f` por WS + `/api/strat_f` (#7) |
| `hub/static/index.html` | **REESCRITO** a panel STRAT-F (#7) |
| `scanner.py` | acumula `record_strat_f` y lo empuja al HUB (#7) |

### Fase 4 — Documentación de ingeniería (SRS/ADR/ERD/API/ATDD)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 8 | `engineering_docs` | ✅ done | #1–#7 |

> **Documentación de ingeniería completa** (2026-07-11). En `docs/engineering/`:
> `SRS.md` (objetivo 5 entradas/2h + NFR), `adr/` (3 ADR: evaluador puro,
> SQLite diario, no borrar hub_models), `erd_trade_journal.md`, `api_spec.md`,
> `glosario.md`. Test ATDD `tests/test_window_2h.py` fija el contrato de
> volumen (N1). pytest **282 passed**.

---

## Módulos de documentación (Fase 4)

| Archivo | Contenido |
|---------|-----------|
| `docs/engineering/SRS.md` | Requisitos funcionales (F1–F12) y no funcionales (N1–N9) |
| `docs/engineering/adr/001_evaluador_puro.md` | STRAT-F como evaluador puro (no opera) |
| `docs/engineering/adr/002_sqlite_diario.md` | Diario en SQLite local |
| `docs/engineering/adr/003_no_borrar_hub_models.md` | No borrar hub_models al reemplazar dashboard |
| `docs/engineering/adr/README.md` | Índice de ADR |
| `docs/engineering/erd_trade_journal.md` | Diagrama de tablas del diario |
| `docs/engineering/api_spec.md` | Contrato de hub/server.py (/api/state, /api/strat_f, /ws) |
| `docs/engineering/glosario.md` | Acrónimos SRS/FRS/NFR, SDD/SAD, ADR/RFC, TDD/BDD/ATDD, MCP/RAG/DSPy... |
| `tests/test_window_2h.py` | ATDD: ventana 2h produce >= 5 entradas STRAT-F |

---

## Fase 5 — Go-Live STRAT-F (GAPs G1+G2 de la auditoría)

| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 9 | `strat_f_panel_live` (G1) | ✅ done | #7 |
| 10 | `strat_f_only_mode` (G2) | ✅ done | #4, #9 |

> **G1+G2 cerrados** (2026-07-11). El panel STRAT-F se muestra en el bot REAL
> (no solo `--hub-readonly`) y `STRAT_F_ONLY=True` aisla la ejecución a STRAT-F.
> `tests/test_strat_f_golive.py` (4 tests, TDD). Auditoría:
> `progress/audit_strat_f_go_live.md`.
> **G3 (validación humana):** STRAT-F **confirmada operativa** por el operador
> (2026-07-15). El foco ya no es “que funcione el pipeline”.

---

## Fase 6 — Mejora de STRAT-F con datos (estocástico en entrada)

> **Estado actual del estocástico:** se **calcula y graba** (`stoch_m15`,
> `stoch_contradicts` en black box / scanner). **No** se usa todavía como
> veto ni boost de score en la decisión de entrada. Eso es intencional
> (`boblioteca/estocastico/04_`, `06_`): medir → A/B → promover.

| Paso | Qué | Estado | Criterio de salida |
|------|-----|--------|--------------------|
| D1 | Operar y **recolectar** señales/trades con stoch en caja negra | 🔄 en curso | Volumen suficiente de WIN/LOSS con `stoch_m15` poblado |
| D2 | **Analizar** (scripts `analyze_trades.py` / `deep_analysis.py` + queries black box) | ⏳ pendiente de datos | Informe: win_rate / expectancy por estado stoch, cruce, contradicción |
| D3 | SDD: reglas de **entrada** que saquen provecho del stoch (boost, soft/hard veto, M5 timing si aplica) | ⏳ solo con evidencia de D2 | Spec aprobado + tests; no hardcodear fe sin datos |

Hipótesis a validar (no son features todavía):

- Extremos M15 (K/D ≥80 o ≤20) alineados con dirección STRAT-F suben expectancy.
- Cruces en zona de banda refuerzan el timing de entrada (hoy se desaprovecha).
- `stoch_contradicts=true` predice peores resultados → candidato a soft/hard veto.

**No reabrir** features #1–#7. Cualquier cambio de reglas de entrada = feature nueva con SDD.

---

## Fase ops (paralela, no bloquea STRAT-F)

| ID | Feature / fix | Estado | Notas |
|----|---------------|--------|-------|
| 8 | `schedule_auto` | 🔄 in_progress | Consola work/rest/day-cap; impl T1–T7 hecha |
| — | `duration_live` | 🔄 review | DURATION_SEC live (no import congelado) |
| — | Tests vs `hub_bankroll.json` min_payout=90 | known issue | Contamina STRAT_*_MIN_PAYOUT; ~24 fails en suite |

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-07-19 | **Feature #16 — Re-chequeo M15 al promover desde maturing_watchlist (STRAT-F) DONE**: corrige la entrada contra-tendencia M15 visible (~30% de aceptadas, 13/43 en auditoría). Causa raíz: la sala de espera (`maturing_watchlist`) promovía con el `m15_context` de la DETECCIÓN, no el actual; si la tendencia viró, la entrada salía contra-tendencia sin re-chequeo (R1 de `evaluate_strat_f` no se aplicaba en promoción). Solución (teoría de agotamiento de Ruben): al promover se re-evalúa M15 actual; alineado→promueve; contra-tendencia→SOLO promueve si stoch M5 confirma agotamiento (CALL contra-M15-bajista %K<20; PUT contra-M15-alcista %K>80), si no→DROP (no opera, no consume Massaniello). Archivos: `src/strat_fractal.py` (`recheck_m15_alignment`, `stoch_m5_exhausted`), `src/scanner.py` (re-chequeo en bloque `mark_promoted` + fix `stoch_m15=None` por bug preexistente `UnboundLocalError` con `_eval_override`). Tests: `tests/test_strat_f_maturing_recheck.py` (13 passed, R1-R5). Sin regresiones (21 failed pre-existentes sin cambio vs baseline). SDD: `specs/strat_f_maturing_m15_recheck/`. |
| 2026-07-18 | **Validación Wyckoff Fase C — FASE 1 (recolección 40/40) + FASE 2 (análisis, sin edge)**: config bot a SOLO vencimiento 5min (`MULTI_DURATION_DATA_COLLECTION=False`, `MULTI_DURATION_SECS=(300,)`) para que el filtro FASE1 `entry_duration_sec=300` coincida. Recolección demo cuenta-only a 40 filas (300s + spring_margin NOT NULL + outcome WIN/LOSS + scanned_at>=inicio experimento). Resultado FASE1: 40/40 alcanzadas. **FASE 2 (observacional, sin tocar decisión/score):** baseline WR 47.5% (19W/21L); spring_margin median=0.0, Q3=0.0176 (mayoría ~0, pocos valores altos); buckets por cuartiles y thresholds fijos (>=0.01..0.10) máximo +2.5pp vs baseline. **NINGÚN threshold alcanza el umbral de capital 8pp fijado ANTES de datos** → FASE 3 (port a SSD) NO procede con n=40. Decisiones de operación de soporte: (a) separación limpia Gestión Massaniello vs Modo 24h en dos flags/endpoints/botones independientes (`STAKE_MODE` solo monto, `DAILY_LOSS_GUARD_ENABLED` solo frenos); (b) `STAKE_MODE=fixed` → executor usa `FIXED_STAKE_USD` sin Massaniello; (c) `DAILY_LOSS_GUARD_ENABLED=False` → `continuous_mode.should_skip_scan`/`should_stop_entirely` no pausan (modo 24h sin límite diario); (d) botón STOP del hub ahora cierra también el server (`_force_exit_cleanup`) para poder cerrar durante reconexión. Archivos: src/config.py, src/executor.py, src/continuous_mode.py, app.py, hub/static/index.html. Verificado AST + 26 tests (webapp_lifecycle, multi_duration, spring_heuristic). |
| 2026-07-17 | **FASE 0 — spring_margin (float) reemplaza spring_confirmed (bool)**: el binario estaba sesgado estructuralmente a 1/NULL por STRAT_F_ZONE_MIN_AGE=3 (filtro de edad garantiza >=3 velas 5m post-fractal, mínimo casi siempre >= band). Ahora `spring_margin` = (min/max post-fractal - band)/band*100, continuo y con signo (positivo=no rompió, negativo=rompió). Campo `spring_margin REAL` en `trade_journal.candidates` (dejé `spring_confirmed INTEGER` como columna muerta por compatibilidad). Misma heurística `_spring_heuristic_5m1m`, mismo punto de integración (strat_fractal.py:314 return, scanner.py log/_rec, trade_journal log_candidate). SOLO logging, sin tocar if de aceptación/rechazo ni score. 7 tests actualizados (test_spring_heuristic.py) + smoke DB REAL con decimales (0.0455, -0.0416, None). Plan de 5 fases (Validación Wyckoff Fase C) documentado en progress/current.md con umbral 8pp fijado ANTES de datos. |
| 2026-07-17 | **spring_confirmed (heurística OBSERVACIONAL, NO SSD)**: etiqueta cada señal STRAT-F aceptada con `spring_confirmed` (INTEGER 1/0/NULL en `trade_journal.candidates`). SOLO logging: no altera decisión/dirección/score. Función `_spring_heuristic_5m1m` (nombre explícito de heurística, NO el StochasticSpringDetector real). Regla: CALL (fractal_down) → mínimo de velas 5m post-fractal [i+1:i+4] vs band (low fractal); si >= band → 1 (spring), si rompió → 0; si no hay post-5m suficientes usa últimas 2-3 M1; si tampoco → NULL. Espejo para PUT. Log `[STRAT-F] ✓ ... spring=` + columna en DB. Protocolo de análisis fijado en progress/current.md (umbral ≥8pp win-rate 1-vs-0, muestra ≥30/grupo, NULL excluidos del análisis). 7 tests nuevos (test_spring_heuristic.py) + smoke DB INTEGER OK. |
| 2026-07-17 | **Track módulo `m1_micro_confirm.py` + test**: archivos locales sin trackear (untracked) desde 2026-07-16. Commiteados aparte (sin tocar lógica): confirm_m1_micro (gate M1 micro-trend, fail-open) + 13 tests. Auditoría confirmó: `fetch_candles_1m` (candle_patterns.py:223) pide 5 velas M1 terminando 300s en el pasado -> NO hay repaint de vela en formación en M1 (descarta hipótesis B). |
| 2026-07-17 | **Fix maturing `mark_promoted` (hermano de upsert_young)**: `mark_promoted(self, key, *, mode=...)` es keyword-only; mi llamada le pasaba `("shadow"/"live")` posicional → `takes 2 positional but 3 given`. Corregido en `_apply_strat_f_result` (`mode=args[1]`). No-fatal pero mataba la promoción a watchlist. Detectado en vivo (log `mark_promoted falló`). |
| 2026-07-17 | **Fix `ENTRY_MAX_LAG_SEC` (timing de entrada)**: restaurado a `1.5` (era `0.3`). El valor `0.3` (commit 377c87e, comentario "0.3ms guard") era un error de unidad — `entry_sync.py` lo usa como SEGUNDOS, no ms. Con 0.3s el bot rechazaba toda orden por `REJECT_LATE_ENTRY` (lag real ~0.44s post-open de vela de 300s). Diagnóstico coincide con auditoría externa: el event-loop-block por HTF durante buy ya estaba resuelto en código (Fix F6k: cancelar task HTF antes de `buy()` + `await asyncio.sleep(0)`; fetch pesado en `to_thread`/`run_in_executor`). El log de timeout de `trade_client fresco` era de un estado anterior (Pitfall J ya removió el trade_client). |
| 2026-07-17 | **parallel_scan_fase3 (id 15) AUDITADO + CORREGIDO en vivo**: la entrega inicial (commit e59be7e) tenía STRAT-F MUERTA en producción a pesar de 4 tests verdes — el dispatch `_run_strat_f_parallel` quedó DESPUÉS del `return` de `_scan_phase_evaluate_assets` y en método equivocado (`radar_watch_tick`), así que `pending_f_ctxs` se llenaba pero nunca se evaluaba (`STRAT-F ok=0` siempre). 2do bug: `upsert_young` llamada con dict posicional vs firma keyword-only → 6 errores/ciclo. Auditoría en vivo (log de diagnóstico temporal + correr el bot 1 ciclo) detectó ambos. Corregido: dispatch movido a `_scan_phase_evaluate_assets` antes del `Eval` (línea ~1437); `_apply_strat_f_result` desempaqueta `upsert_young(**args)`. Re-validado en vivo: `STRAT-F ok=1..5`/ciclo, 0 errores maturing. Ver `agent/HANDOFF.md`. |
| 2026-07-17 | **parallel_scan_fase3 (id 15) done (PRIMERA ENTREGA)**: STRAT-F de FASE 3 del scanner evaluada en ProcessPool (10 workers = 50% de 20 cores); STRAT-A intacta. Speedup 2.19x (benchmark N=40). 4 tests verdes. Mejoras operativas: arranque inmediato (sin despertador), `SESSION_MAX_MIN=0` (sin corte 60 min), `ALIGN_SCAN_TO_CANDLE=False` (scan cada 60s con countdown). Fix WS runtime (reconexión en _resolve_trade + wait_while_trade_open) cerrado en sesión previa. |
| 2026-07-15 | **Doc sync:** STRAT-F marcada operativa; Fase 6 = datos + estocástico en entrada; G3 cerrado por validación humana; ops (`schedule_auto`, `duration_live`) documentados aparte. |
| 2026-07-14 | **Hub bankroll Massaniello**: capital/Ops/ITM/payout en Operación; stake en vivo; `GET /api/massaniello/preview`; min_payout unificado en escáner. **Resolve lag**: no forzar LOSS con profit=0; grace/timeout amplios. Lifecycle session bootstrap (Iniciar/resume). Log compacto (`BOT_LOG_VERBOSE`). |

| 2026-07-11 | Borrado de `feature_list.json` viejo y `docs/ROADMAP*.md` (mintieron sobre strat_b) |
| 2026-07-11 | Creación de roadmap STRAT-F (feature #1 en curso) |
| 2026-07-11 | Reemplazo del dashboard por panel STRAT-F (#7): `hub/strat_f_state.py`, `hub/strat_f_panel.py`, `hub/parser.py`, `hub/render.py`, `hub/server.py` + `index.html` reescrito |
| 2026-07-11 | Documentación de ingeniería (#8): `docs/engineering/` (SRS, 3 ADR, ERD, API Spec, glosario) + `tests/test_window_2h.py` (ATDD ventana 2h). pytest 282 passed |
| 2026-07-11 | **Go-Live GAPs G1+G2 cerrados**: panel STRAT-F cableado al bot real (`_flush_strat_f_panel` en `scan_all` + `StratFPanel` en `ConsolidationBot` + `server.init` lo usa por WS) y modo `STRAT_F_ONLY` que aísla la ejecución STRAT-F. `tests/test_strat_f_golive.py` (4 tests). pytest **286 passed**. Falta G3 (end-to-end en máquina de Ruben). |
