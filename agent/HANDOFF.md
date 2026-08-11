# HANDOFF — Session Transfer Document

> **Read this first** after `PROJECT_STATE.md` when resuming work.
> **ÚLTIMA SESIÓN: 2026-08-07 — Cierre definitivo del hilo del clustering (EXP-075 + EXP-074b-NULL).**
> Feature 38 `lab_protocolo_cientifico` = DONE y pusheada (commit `dc53c97`).
> NUEVA FASE del lab: de "buscar la vela mágica" → "modelar el comportamiento del mercado".

---

## ⭐ SESIÓN 2026-08-08 — AUDITORÍA FUNNEL 5m/M15 (freno+arcoíris+estocástico) — CIERRE

**LEER PRIMERO al retomar.** Hoy se auditaron combinaciones de freno + arcoíris + estocástico
en M5 y M15 con entry/exit en 5min y señal a 15min de expiración, por petición del Trader-Humano.
Autonomía de 30min sin preguntas para llegar a 60% WR (NO alcanzado).

### Qué se hizo
1. **EXP-FUNNEL-5M** (freno+arcoíris+estocástico, M5, 30 combos sistemáticos): WR 44-52% en
   8 datasets (EURUSD 2022/23/24/25, XAUUSD 2020/21/23/24) → **REFUTADO** (moneda). El experimento
   especial (freno→arcoíris full→salida estocástica→15min) dio 45-49%. BUG corregido: exit_off 2→3
   (15min real) y scross N=0 (gate inicial bloqueaba re-chequeo). Reporte: `reports/AUDITORIA_FUNNEL/exp_funnel_5m.md`.
2. **EXP-MTF** (arcoíris M15 como filtro de tendencia + trigger M5): 9 modos en `audit_multitf.py`
   + 4 modos M15 puro en `audit_m15_pure.py`. 4 datasets (EURUSD 2023/24, XAUUSD 2023/24).
   Máximo robusto = **56-57%** (mtf_cross_ema / mtf_cross_ema_s, XAUUSD 2024, n>700, p<0.0002).
   Con expiración real 15min (xo=3) TODO cae a 48-52% (moneda). **NO se llegó a 60%.**
   Reporte: `reports/AUDITORIA_FUNNEL/exp_mtf.md`.
3. **Contexto previo confirmado**: el arcoíris M15 dio 71% en EXP-EDF-04 COMO GATE del Edificio
   (embudo P1→P2→P3 validado). Aislado o con triggers M5 su edge se diluye a 54-57%. La diferencia
   es la ESTRUCTURA del Edificio, no los indicadores.

### Decisión tomada
- El límite honesto de "indicadores en M5/M15 sin el embudo del Edificio" es ~57% WR.
- Para 60%+ en datos reales, la vía es recuperar la ESTRUCTURA del Edificio (indicadores como
  filtros DENTRO del embudo P1→P2→P3 ya validado), no como señal independiente.

### Dónde quedamos
- La rama M5/M15 aislada está Agotada (moneda o techo 57%). No seguir por ahí.
- Abierta la rama: arcoíris M15 + embudo P1→P2→P3 del Edificio (replicar EXP-EDF-04 pero con
  freno/arcoíris/estocástico como filtros del Edificio, no señal suelta). Pendiente OK del TH.

### Archivos clave de la sesión (SIN commitear — ver bloqueo abajo)
- `scripts/audit_funnel_5m.py` (30 combos M5, freno+arcoíris+estocástico)
- `scripts/audit_multitf.py` (9 modos M15→M5)
- `scripts/audit_m15_pure.py` (4 modos M15 puro)
- `scripts/audit_edificio_funnel.py`, `audit_exp_edf.py`, `exp_funnel_b.py`, `exp_funnel_valvula.py` (base)
- `reports/AUDITORIA_FUNNEL/{exp_funnel_5m.md, exp_mtf.md, exp_valvula_P3.md, exp040_motor_real_m15_m5.md, exp_edf_*.md}`
- Mis modifs (validadas 21 passed): `src/edificio_contratacion.py` (fix P2→P3 + válvula [NO ADOPTADO]),
  `src/config.py` (flags EDIFICIO_P3_* [NO ADOPTADO]), `tests/test_edificio_contratacion.py`.

### ⚠ BLOQUEO DE COMMIT (heredado, NO de esta sesión)
- 3 archivos en conflicto de merge sin resolver BLOQUEAN cualquier commit:
  `specs/lab_protocolo_cientifico/EXP-EDIFICIO-NN-SCORE/{HANDS_FREE_ORDER,design,validation}.md`
  (del push pendiente de la sesión 2026-08-07, ya documentado como "PUSH PENDIENTE divergencia remoto").
- NO se resolvieron (trabajo ajeno, protocolo CLOSE: no tocar trabajo ajeno). Mi trabajo de la
  sesión quedó SIN commitear (scripts/reports staged pero commit bloqueado por los U files).
- Al retomar: el usuario debe resolver esos 3 conflictos (o `git merge --abort` / rebase) ANTES de
  poder commitear el trabajo de hoy. NO push sin OK.
- `init.ps1` en rojo: 22 tests rotos, TODOS del bot STRAT-F (`test_executor`, `test_consolidation_bot`,
  `test_session_lifecycle`, etc.), PRE-EXISTENTES (heredados, no causados por esta sesión).
  `test_edificio_contratacion.py` = 21 passed (lo único que esta sesión tocó).

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
    - **2026-08-07 (AUTORIZADO) — Databento / CME 6E, adquisición pequeña OHLCV 1m (NO MBO)**: proveedor
      Databento, dataset `GLBX.MDP3`, símbolo continuous `6E.v.0` (volume roll), `volume`=contratos
      reales, UTC, período 2022-2026. **BLOQUEO DE ACCESO: cliente `databento` 0.83.0 instalado PERO
      SIN API key** (ni env, ni .env) → aún NO se descargó nada. Scripts `scripts/lab_ew_acquire_cme.py`
      (descarga 1m) y `scripts/lab_ew_verify_cme.py` (checklist + inspección de rollovers) listos sin
      ejecutar. EW pasa a ser hipótesis sobre **EUR/USD Futures 6E** (no spot); resultados NO comparables
      1:1 con EXP-071..075. **Falta la API key para correr acquire→verify.** NO se ejecutó EW-1/2/3.
    - **2026-08-07 (NO PAGAR aún) — BÚSQUEDA GRATUITA para CME 6E**: el Trader-Humano ordenó NO comprar
      Databento y buscar fuente gratuita (Barchart, contratos individuales, export OHLCV intradía).
      Búsqueda read-only: NO existe fuente gratuita con M15/1-min de 6E y cobertura 2022-2026 completa.
      Kaggle individuales 2000-2022 (no llega a TEST); Yahoo `6E=F` da M15 solo 60d pero DIARIO 2022-2026
      COMPLETO con volumen real (0.52% ceros). Única vía gratuita completa = **EW en DIARIO con `6E=F`**
      (desvía spec M15→D, requiere aprobación). Barchart 1 descarga/día inviable; CME solo diario (validación).
      Alternativas presentadas: (A-gratis) diario Yahoo; (C-pago) Databento M15; (B) M15 60d insuficiente.
    - **2026-08-07 (EW-1 EJECUTADO + AUDIT + RETRACCIÓN):** congelado y ejecutado `scripts/lab_ew1_autocorrelacion.py`
      (autocorrelación Ljung-Box de eficiencia/absorción, D1, 1,144 barras válidas, Opción 2). **Primer pase
      FALSO:** reportó "20 lags significativos en TRAIN y TEST" → Hermes declaró "SEÑAL OOS justifica M15".
      AUDIT descubrió defecto metodológico: `eficiencia` no estacionaria (Ljung-Box arrastraba tendencia) y
      `absorcion` binaria mal especificada. **RETRACCIÓN 1:** ese veredicto era falsa alarma. Tras corregir
      (Δeficiencia estacionaria, absorción centrada), seguía saliendo "20 lags"; segundo AUDIT (temp
      hermes-verify-ew1-diag.py, ya borrado) ancló: Ljung-Box correcto (12/200 rechazos en ruido blanco),
      Δeficiencia ACF lag-1 = **-0.52** en TRAIN y TEST, lags 2-5 ≈0. O sea MA(1) de REVERSIÓN de 1 paso, no
      memoria de energía direccional. **RETRACCIÓN 2:** "justifica M15" también era falsa alarma. Veredicto
      final honesto: `reversion_ma1_mecanica` — efecto mecánico del ratio move/vol, NO esfuerzo/resultado
      Wyckoff. **EW (como memoria direccional) NO halla lo que buscaba → NO justifica pagar Databento M15.**
      Reporte inmutable: `data/strategy_lab/ew_reports/EW-1/`. **NO se pagó Databento. NO se ejecutó EW-2.**
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

---

## ⭐ SESIÓN 2026-08-07 NOCHE — EXP-POI-STOCH + EXP-EDIFICIO-NN-SCORE + POI HUMANIZADO

**LEER PRIMERO al retomar.** Hoy se corrió la serie de experimentos del Edificio sobre
EURUSD_otc (datos OTC, no spot) y se rediseñó el POI a petición del Trader-Humano.

### Qué se hizo
1. **EXP-POI-STOCH** (commit `87ff7c2`): POI+estocástico sobre EURUSD_otc M15.
   H1=REFUTADA, H2=INCONCLUSA (no replica OOS), H3=REFUTADA. EURCHF_otc no disp (Token rejected).
2. **EXP-POI-STOCH M1** (commit `ff25eb1`): H2 en M1 (POI M1 + |K-D|≥25 → retrace).
   TRAIN OR=2.55 (p≈0) pero TEST OOS OR=1.09 IC[0.72,1.63] incluye 1 → **REFUTADA** (no-estacionariedad).
3. **EXP-EDIFICIO-NN-SCORE** (commit `7731d81`): LightGBM sobre 17 features que el Edificio YA calcula
   (edificio_events.parquet, 946 eventos, label `win`, split temporal 70/30). H1=ACEPTADA (AUC OOS 0.548>0.505),
   H2=REFUTADA (top-k lift IC incluye 0), H3=ACEPTADA (calibración ECE 0.012 vs 0.278 baseline).
   Conclusión: la red rankea/calibra mejor pero NO crea edge (win base 0.363, lejos de break-even ~0.55).
4. **POI HUMANIZADO DINÁMICO** (commit `2fb9a0e`): el Trader-Humano pidió mejorar el POI porque
   "no se calcula como es". El POI original (swing_levels_causal min_touch=2,tol=5,swing_k=2) daba
   1104 niveles / 14269 eventos = ruido. Rediseñado como **zonas que nacen en pivote estructural y
   MUEREN por breakout** (swing_k=8, tol=0.5×ATR, min_touch=3, bounce≥0.5, muerte=cuerpo≥0.6×ATR contra zona).
   Resultado: **264 zonas / 2669 eventos / 10 vivas al final** — mucho más ordenado.
5. **CHECK evento** (commit `2fb9a0e`): idx=2609 = PUT en resistencia 1.14830. Pierde a H=1,2,3,4 M15
   (precio subió), gana solo a H=5. Confirma: el POI bien dibujado NO da edge direccional a H corto.

### Decisión tomada
- El POI del experimento era ruido (laxo). El POI dinámico (nace/muere por breakout) es el que se parece
  al POI real del Trader-Humano. PERO la zona bien dibujada ≠ entrada ganadora: el evento 2609 lo prueba.
- Arquitectura confirmada: Wyckoff/POI = CONTEXTO/FILTRO, no gatillo. El Edificio rankea mejor con red
  pero no hay edge utilizable en binarias de H fijo.

### Dónde quedamos
- POI humanizado dibujado y validado a ojo (imágenes en reports/EXP-POI-STOCH/). Falta: re-correr
  H1/H2 de EXP-POI-STOCH con el POI dinámico para ver si deja de estar refutada (PENDIENTE OK del TH).
- También pendiente: chequear tasa de acierto de VARIOS eventos POI a H=1..5 (no solo el 2609).

### Archivos clave de la sesión
- `scripts/lab_exp_poi_stoch.py`, `lab_exp_poi_stoch_m1.py`, `lab_exp_poi_stoch_h2_m1_oos.py`
- `scripts/lab_exp_edificio_nn_score.py`
- `scripts/lab_poi_visual_check.py`, `lab_poi_humanizado.py`, `lab_poi_dinamico.py`, `lab_poi_check_event.py`
- `reports/EXP-POI-STOCH/{summary.txt, h1_results.csv, h2_results.csv, m1_analysis.txt, h2_m1_oos.txt,
  poi_full_events.png, poi_sequence_example.png, poi_dinamico_full.png, poi_dinamico_seq.png}`
- `reports/EXP-EDIFICIO-NN-SCORE/{summary.txt, topk_table.csv, feature_importance.csv, protocol_frozen.json}`
- `specs/lab_protocolo_cientifico/EXP-POI-STOCH/`, `EXP-EDIFICIO-NN-SCORE/` (HANDS_FREE_ORDER incluidos)
- Datos: `src/strategy_lab/results/edificio_events.parquet` (946 eventos, label `win`, split OOS)
- OTC crudo: `tools/quotex-historical-data/EURUSD_otc_60s_365days.csv` (76835 velas M1)

### Reglas que NO romper
- Una feature a la vez. NO push ciego (ver nota de push abajo).
- Edificio caja negra intacta; no tocar src/ para meter POI.
- Datos OTC = validación; NO se compara 1:1 con spot.
- El POI humanizado es el que se parece al del Trader-Humano; no volver al laxo.

### ⚠ PUSH PENDIENTE (divergencia con remoto)
- HEAD local = `2fb9a0e` (3 commits adelante: ff25eb1, 87ff7c2, 7731d81, 2fb9a0e... en realidad
  3 del lab + el de hoy). El remoto origin/main tiene **4 commits adelante** (otro Hermes pusheó
  EXP-EDIFICIO-NN-SCORE `1c73b5d` y más). `git push` RECHAZADO (non-fast-forward).
  `git pull --ff-only` NO puedo (divergen, necesita merge o rebase). **NO hice force ni merge.**
  AL RETOMAR: integrar los 4 commits del remoto (pull/rebase) y luego push, con OK del usuario.
  Estado seguro: mis commits están locales, repo sin archivos sueltos de la sesión (todo commiteado).

