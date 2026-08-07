# HANDOFF — Session Transfer Document

> **Read this first** after `PROJECT_STATE.md` when resuming work.
> **ÚLTIMA SESIÓN: 2026-08-07 — Cierre definitivo del hilo del clustering (EXP-075 + EXP-074b-NULL).**
> Feature 38 `lab_protocolo_cientifico` = DONE y pusheada (commit `dc53c97`).
> NUEVA FASE del lab: de "buscar la vela mágica" → "modelar el comportamiento del mercado".

---

## ⭐ ESTADO ACTUAL (2026-08-06) — LEER PRIMERO

### Qué se hizo (sesión 2026-08-06 tarde — paradigma Wyckoff + freno científico)
- El laboratorio EVOLUCIONÓ de "buscar la vela ganadora" a "modelar el
  comportamiento del mercado" (paradigma Wyckoff del Trader-Humano):
  - **EXP-071** Zona de Descubrimiento: contexto [extremo>freno>cruce] vive ~45
    velas; tras filtrar n≥100 solo pinbar/continuacion sobreviven, ambos EV neg,
    FDR 0.018. NINGÚN confirmador tiene edge. (commit efa212b)
  - **EXP-072** Mapa de Transiciones (Markov sobre estados régimen×pendiente×
    impulso): mercado mean-reverting (auto-bucle 0.50-0.54), el impulso del
    estocástico SE REVIERTE (rate 0.28-0.30), 0 estados con favorable>0.55.
    Fase A: dur mediana 25, 1er freno 6, 1er cruce 2, 5 oscilaciones, sep K-D 15.2.
    (commit 76d467b)
  - **EXP-073** Dinámica de la Fase A (energía, no eventos): 3308 fases, ninguna
    variable dinámica de K-D predice la resolución (FDR 0/8). El estocástico
    describe POSICIÓN, no ENERGÍA/control. (commit d696aba)
  - **EXP-074** Clustering no supervisado de Fases A (19 features + energía
    Wyckoff): K=2 (sil 0.2185), 807/2500 (24% explosivo / 76% lateral).
    Hipótesis de población mixta APOYADA. (commit ca8035f)
  - **EXP-074b** Estabilidad de Clusters (freno científico, 6 pruebas de
    Grok/ChatGPT): RECHAZA la partición GMM como robusta — NO sobrevive a cambio
    de algoritmo (ARI ~0), ablación de features (9.7%→48.1%), ni bootstrap (rango
    22%→95%). Lo REAL: duración de la Fase A es variable continua (ruptura corta
    vs lateral larga), no 2 poblaciones profundas. PRUEBA 3 OOS NO ejecutó
    (dataset empieza 2022, no hay 2012-2018). (commit c4ecb42)
  - **2026-08-07 — CIERRE DEFINITIVO del hilo del clustering** (orden Trader-Humano):
    - **EXP-075** Duración/Tipo de Fase A como variable CONTINUA (re-enfoque de 074b):
      REDIME la PRUEBA 3 OOS (dataset ya llega a 2026). 3307 fases, TRAIN 2022-2024 /
      TEST 2025-2026. FDR-BH sobre 36 descriptores continuos = **0/36 significativos**;
      OR por cuartil de `duration` ≈1.0 (TRAIN y OOS), bootstrap IC incluye 1.0.
      **RESULTADO NEGATIVO**: duración continua NO predice resolución. (commit pendiente)
    - **EXP-074b-NULL** Control nulo / surrogate + Prueba temporal OOS REAL:
      null = shuffle independiente de columnas (B=200) preservando marginales.
      - silhouette null (0.405) > REAL (0.2185): el null es geométricamente más favorable
        (null "fuerte") → NO se usa silhouette para refutar.
      - OOS TRAIN 2022-2024 → TEST 2025-2026: TEST 100% "corto" → **colapso total**
        (diff 81.8pp, silhouette TEST=nan). **No hay estabilidad temporal.**
      - %minoritario REAL 24.4% en el borde del null (máx 21.6%).
      - **VEREDICTO: hipótesis de población mixta NO SOPORTADA** como régimen estable del
        mercado. El clustering es geometría del método, no régimen natural.
      - Matiz honesto documentado: el criterio congelado sil_REAL>p95_null daba MIXTO;
        se explica por qué el null es favorable y el veredicto se apoya en OOS + %minoritario.
    - **Hilo del clustering CERRADO**: ni binario (074b) ni continuo (075) predice nada.
    - **DISEÑO (no ejecutado) Energía Wyckoff**: volumen+rango+resultado, no estocástico.
      Variables esfuerzo/resultado/eficiencia/absorción/climax/compresión. Pregunta inicial:
      ¿contienen memoria/estructura de transición que el K-D M15 no contiene? Aprobación
      pendiente para correr EXP-EW-1 (autocorrelación de energía vs estocástico).
    - **2026-08-07 (tarde) — BLOCKED por instrumento (NO resultado negativo)**: el EURUSD M15
      disponible trae `tick_volume` (no volumen real) con ~55% de ceros (62912/114237 velas).
      Eso hace `effort`/`efficiency`/`absorption` artificiales/indefinidas → NO se ejecuta EW-1
      (ni filtrando tick_volume>0: sesgo de selección). Decisión Trader-Humano = opción C:
      cerrar SOLO el uso de este dataset, NO la hipótesis. Se escribió `DATA_REQUIREMENTS_EW.md`
      (qué es volumen real, campos mínimos, umbral ≤2% ceros, cobertura ≥3a M15, checklist de
      6 pasos de verificación antes de congelar EW-1). Conclusión: "Hipótesis NO EVALUADA por
      insuficiencia del instrumento de medición".
    - **2026-08-07 (tarde, decisión A) — candidato local EVALUADO y RECHAZADO**: se revisó el
      EURUSD_M1 de Dukascopy ya en `SMC-SYSTEMS/data/raw` (el repo lo usa vía `build_m15_from_m1.py`,
      renombrando a `volume`=suma de ticks). Tiene **99.7% de ceros en volumen M15** (tick volume
      del banco) — peor que HistData. FX spot OTC no tiene volumen centralizado; el tick volume de
      cualquier feed individual es disperso/cero. NO se descargó nada nuevo, NO se congeló EW-1.
      Pendiente decisión A1 (evaluar futuros CME, volumen de bolsa real) o A2 (aceptar bloqueo).
      NO se ejecutó EW-1/2/3.
    - **2026-08-07 (decisión A1) — CME 6E EVALUADO por factibilidad/semántica (SIN descarga)**: el
      candidato CME Euro FX Futures `6E` (125k EUR/contrato) da `volume` = nº de contratos en central
      limit order book CME = **REAL traded volume** (no tick, no proxy). Cubre M15 histórico vía
      Databento/Polygon/CME; pasa split OOS 2022-2024/2025-2026. Limitación spot→futuros: cambia el
      instrumento experimental a EUR/USD futures (no spot); rollover introduce saltos en PRECIO (no en
      volumen). MEJORA la validez de EW al dar volumen centralizado. **Aprobado conceptualmente;
      pendiente autorización del Trader-Humano para la ADQUISICIÓN de datos (elegir proveedor) antes
      de descargar/modificar pipeline/congela EW-1.** NO se ejecutó EW-1/2/3.
  - **Art. 13 + ADR-005** añadidos al Charter: EURUSD REAL = SOLO descubrimiento;
    validación OTC obligatoria del propio lab antes de promover al Edificio.
    (commit efa212b)

### Decisión tomada
- Paradigma cambiado por el Trader-Humano: el lab ya no busca "la estrategia" ni
  "el confirmador mágico"; construye un MAPA PROBABILÍSTICO de evolución del
  mercado (Wyckoff: estado→transición→confirmación→operación).
- FRENO CIENTÍFICO aplicado (Grok/ChatGPT): NO procede EXP-075 sobre el cluster de
  GMM porque la partición no es estable. El lab evitó construir estrategia falsa.
- **2026-08-07**: el hilo del clustering quedó CERRADO formalmente (EXP-074b + EXP-075
  negativos + EXP-074b-NULL con OOS colapsando). El estocástico M15 describe ESTADO,
  no CONTROL ni transición. No se promueve nada al Edificio (Art. 13).

### Próximo paso sugerido (al retomar)
- **PENDIENTE APROBACIÓN del Trader-Humano (opción A/B)**: el dataset EURUSD M15 actual está
  BLOQUEADO por instrumento (tick_volume, 55% ceros) — NO es resultado negativo. El diseño de
  Energía Wyckoff sigue VIVO como hipótesis. Definido `DATA_REQUIREMENTS_EW.md` (qué es volumen
  real vs tick volume, campos mínimos, umbral ≤2% ceros, cobertura ≥3a M15, checklist 6 pasos).
  - (A) Si el Trader-Humano aprueba buscar feed adecuado y pasa el checklist → congelar EW-1.
  - (B) Si no hay datos adecuados → abandonar la vía (hipótesis no falseada, solo no evaluada).
  - NO buscar dataset por cuenta propia hasta decisión. NO ejecutar EW-1/2/3.

### Archivos clave para retomar
- `docs/LAB_CHARTER.md` (principios inquebrantables, Art.1–12)
- `docs/specs.md` (ciclo de vida + checklist Art.6/10/11/12)
- `specs/lab_protocolo_cientifico/` (requirements/design/tasks/trader_humano_review)
- `scripts/lab_run.py`, `scripts/lab_ci.py`
- `src/strategy_lab/experiment_runner.py`
- `src/strategy_lab/secuencia_libre.py`, `optimizer.py`, `run_lab_secuencia.py`

### Reglas que NO romper al retomar
- Una feature a la vez. SDD obligatorio para features `sdd:true`.
- No push sin OK. Commit = solo trabajo de la sesión (nunca `git add -A` ciego).
- Bot corre PRACTICE por defecto; NUNCA REAL sin OK explícito.
- Datos REAL (EURUSD) = descubrimiento; OTC = validación final.
- Trader-Humano revisa specs; usuario aprueba antes de implementar.

---

## ⭐ Estado de estrategias (DEUDA SALDADA — leer antes de cualquier otra cosa)

- **STRAT-A**: primer paso hacia el Edificio — etapa **conclusa**, misión cumplida.
- **STRAT-F y todas las demás estrategias**: **archivadas**, etapa concluida.
- **Edificio de Contratación** (`src/edificio_contratacion.py`): **ÚNICA estrategia activa** y **FINAL para operar en REAL**.
- NO reactivar estrategias archivadas sin pedido explícito del usuario.
- Todo lo que sigue en este documento describe la era STRAT-F: es historia, no estado actual.

---

## What is true right now

1. **STRAT-F pipeline completo** (prefetch M15, evaluador, scanner, filtros, panel hub, `STRAT_F_ONLY`).
2. **Estocástico M15 = ACTIVE help** (`#9 done`):
   - `STOCH_HELP_MODE=hard` default — veto extremo contrario, boost a favor.
   - `src/stochastic_zones.py` + wire en `scanner.py`; `strat_fractal` intacto.
3. **Place-order inteligente** (`#10 done`): prewarm, alt retries, `last_order_attempt` en hub, quarantine 5.
4. **24/7 data collection**: fin de ciclo Massaniello → **solo reset** Massaniello; bot **no para**.
   - `CONTINUOUS_DATA_COLLECTION_MODE=True` + `SESSION_AUTO_RESET_ON_COMPLETE=True`.
5. **Scan alineado a open vela 5m**: `ALIGN_SCAN_TO_CANDLE=True`, `SCAN_LEAD_SEC=0`.
6. **Logs limpios**:
   - Countdown de espera: **1 línea** (no spam por segundo).
   - Con trade abierto: **no scan**, solo `En espera de finalizar trade`.
7. **Housekeeping abierto**:
   - `#8 schedule_auto` in_progress (paused).
   - Tests bankroll `min_payout=90` (P1).
   - Gate M1 micro-tendencia pre-buy: **✅ implementado y ON** (`M1_MICRO_CONFIRM_ENABLED=True`).
8. **Watchdog 24/7 (2026-07-19, #17 done)**:
   - `scripts/watchdog_bot.py` corre como cron cada 5 min. Chequea API (`127.0.0.1:8080`) + proceso + marker "Connection to remote host was lost" en `consolidation_bot.log`; si cae → cleanup + reinicio + loop 24/7.
   - También reinicia si `/api/bot/status` no es `running`/`starting` (meta diaria, ciclo o error). Modo 24h = sin frenos.
   - Log en `scripts/watchdog.log`. 14 tests (`tests/test_watchdog_bot.py`).
9. **Config 24h + vencimiento 10min (2026-07-19)**:
   - `DURATION_SEC=600`, `MULTI_DURATION_SECS=(600,)`, `MASSANIELLO_PRIMARY=600` en disco (pedido usuario).
   - `DAILY_LOSS_GUARD_ENABLED=False` en disco: el loop lee el **módulo** config, no `_runner._config` mutado por `/api/daily-guard`. Antes de este fix, el bot pausaba por daily loss aunque el endpoint dijera OFF.
10. **Math filters + contextual scoring (2026-07-20)**:
    - Nuevo módulo `src/math_filters.py` — Hurst, R², angle, squeeze, composite scorer.
    - Stochastic V2: `k_prev`/`d` keyword-only; vetos solo en cruce confirmado.
    - Scoring contextual 3 niveles: proportional zones + M15 weight + consensus bonus.
    - Duración 900s (600→900 por pedido usuario, reversión temporal).

---

## What remains (priority)

| Priority | Item | Owner |
|----------|------|-------|
| **P0** | Operar 24/7 con math filters + contextual scoring; validar impacto | Human + bot |
| **P1** | Validar M1 micro gate en vivo (log `M1 micro` / REJECTED_M1_MICRO) | Human + bot |
| **P2** | Review/cierre `schedule_auto` + `duration_live` | Agent |
| **P3** | Aislar tests min_payout | Agent |

---

## How to resume

```powershell
cd "C:\Users\v_jac\Desktop\QUOTEX"
.\init.ps1   # puede fallar por min_payout=90; no implica STRAT-F roto
```

Lectura mínima:

1. `docs/CHANGELOG_2026-07-16.md` — todos los cambios de la sesión
2. `agent/PROJECT_STATE.md`
3. Este `HANDOFF.md`
4. `feature_list.json`

---

## Recent sessions

| Fecha | Qué quedó |
|-------|-----------|
| 2026-07-11 | STRAT-F #1–#7 + go-live |
| 2026-07-14 | Bankroll hub, schedule_auto impl, duration_live |
| 2026-07-15 | Docs: foco datos + stoch medición |
| 2026-07-16 | #9 stoch help hard; #10 smart order |
| 2026-07-16/17 | 24/7 Massaniello; align 5m; countdown 1 línea; quiet trade wait |
| 2026-07-17 | **FIX RUNTIME**: cuelgue por WS caído en espera multi-leg. Eliminado trade_client (2ª instancia, Pitfall J CORRECTION); reconexión en _resolve_trade + wait_while_trade_open vía bot.ensure_connection (socket único). Ver `progress/current.md`. |
| 2026-07-17 | **parallel_scan_fase3 (id 15) AUDITADO + CORREGIDO en vivo**: la 1ra entrega (commit e59be7e) tenía STRAT-F MUERTA en producción a pesar de 4 tests verdes — el dispatch `_run_strat_f_parallel` quedó tras el `return` de `_scan_phase_evaluate_assets` y en método equivocado (`radar_watch_tick`). 2do bug: `upsert_young` con dict posicional vs kw-only. Auditoría en vivo detectó ambos; corregido y re-validado (`STRAT-F ok=1..5`/ciclo, 0 errores maturing). (1) arranque inmediato; (2) `SESSION_MAX_MIN=0`; (3) `ALIGN_SCAN_TO_CANDLE=False`; (4) **parallel_scan_fase3** (id 15, done, auditado). |
| 2026-07-20 | **Math filters + contextual scoring (STRAT-F)**: audit vs best practices trading; P0 M1 2-velas, duración 900s; P1 math_filters.py (Hurst/R²/angle/squeeze), Wyckoff range band, stoch V2 (k_prev/d), M15 regresión; P2 scoring contextual 3 niveles (proportional zones + M15 weight + consensus bonus). 73 tests verdes. |

---

## ⚙ Mejoras operativas 2026-07-17 (no bug, calidad de operación)

- **Arranque inmediato**: `consolidation_bot.py` escanea al conectar (sin espera de despertador).
- **Sin límite 60 min**: `config.py SESSION_MAX_MIN = 0`. Massaniello se reinicia
  solo por completitud (SESSION_AUTO_RESET_ON_COMPLETE) en modo continuo.
- **Scan profesional**: `config.py ALIGN_SCAN_TO_CANDLE = False` → cada 60s
  (`SCAN_INTERVAL_SEC`) con cuenta regresiva en 1 línea, cuando no hay trade abierto.
- **parallel_scan_fase3** (feature id 15, status done, AUDITADO+CORREGIDO 2026-07-17):
  - Solo STRAT-F se saca del `for` a `_evaluate_strat_f_serial(ctx)` (pura, picklable)
    y se evalúa en ProcessPool (10 workers = cpu//2). STRAT-A y el resto del `for` INTACTOS.
  - `_run_strat_f_parallel` aplica deltas al loop (caja negra, maturing, logs,
    candidates, reject_counts, batch, stats). `gather(return_exceptions=True)`:
    un worker que falla → `log.error` + `continue`, no aborta el ciclo.
  - ⚠ **BUG CERRADO POR AUDITORÍA EN VIVO**: la 1ra entrega (e59be7e) tenía el
    dispatch `_run_strat_f_parallel` FUERA del flujo real — quedaba tras el `return`
    de `_scan_phase_evaluate_assets` y en `radar_watch_tick`. STRAT-F NO se evaluaba
    (`STRAT-F ok=0` siempre). Corregido: dispatch en `_scan_phase_evaluate_assets`
    ~línea 1437 (antes del `Eval`).
  - ⚠ **BUG 2 CERRADO**: `upsert_young` se llamaba con `dict` posicional pero el
    método real es keyword-only → `_apply_strat_f_result` ahora usa `**args` para
    `upsert_young`. Sin esto, las zonas jóvenes no entraban a maturing (6 errores/ciclo).
  - Degrada a serial si no hay pool (`get_scan_pool() is None`).
  - 4 tests verdes (`tests/test_parallel_scan_fase3.py`); benchmark 2.19x
    (`scripts/bench_parallel_scan_fase3.py`, N=40).
  - Docs: `specs/parallel_scan_fase3/{requirements,design,tasks}.md`.

---

## ⚠ REGLA DE ORO — NO romper de nuevo (runtime WS hang)

Si el bot vuelve a colgarse en "En espera de finalizar trade" tras una caída de
WS, la causa es casi siempre haber reintroducido un `trade_client` / 2ª instancia
de Quotex. RECORDATORIO:

- Las órdenes van SIEMPRE por `enviar_orden(self.client)` en el socket ÚNICO del loop.
- Si el WS cae en la espera, reconectar con `bot.ensure_connection()` dentro de
  `_resolve_trade` (en cada intento) y `wait_while_trade_open` (cada ~15s).
- NUNCA crear un cliente Quotex fresco por orden (idle-timeout → "Connection to
  remote host was lost" en mitad de la espera). Skill: `quotex-bot-runtime-debug`
  → Pitfall J CORRECTION.

Archivos clave de este fix: `src/executor.py` (`_reconnect_if_needed`),
`src/loop_utils.py` (`wait_while_trade_open`), `src/consolidation_bot.py`
(trade_client desactivado).

---

## Files that matter

| Path | Rol |
|------|-----|
| `docs/CHANGELOG_2026-07-16.md` | Documento maestro de cambios |
| `src/stochastic_zones.py` | Stoch help matrix |
| `src/executor.py` | Place-order + Massaniello auto-continue + quiet resolve |
| `src/loop_utils.py` | Align 5m, countdown, wait_while_trade_open |
| `src/scanner.py` | Stoch wire + early return si hay trades |
| `src/config.py` | Flags operativos (stoch, continuous, align) |
| `hub/static/index.html` | last_order_attempt + cycle_rolled toast |
