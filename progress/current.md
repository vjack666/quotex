# Estado de sesión

## FASE TRAZABILIDAD EDIFICIO (F1+F2+secuencia W/L) — 2026-07-31 (APROBADA por Ruben)

### Objetivo
Que las órdenes del edificio queden trazables: (F1) registrarlas en la caja negra
al enviarse, (F2) resolver su resultado WIN/LOSS por TICKET ~1s después del
vencimiento (900s), y llenar la **Secuencia (W/L)** del hub en orden de llegada
(un solo hilo cronológico combinado: STRAT-F + edificio, SIN agrupar W y L).

### Diseño aprobado (investigación completa)

**F1 — Registro en black box al enviar** (`src/edificio_executor.py`, `_send_one`):
- Al confirmar el broker, guardar en la card/evento `order_ref` (índice 3 de
  `place_order` = ticket numérico) además de `order_id` (índice 1).
- Registrar: `record_scan_start("EDIFICIO", scan_number)` → `record_candidate(
  scan_id, "EDIFICIO", {asset, direction, payout: card.payout, score, decision,
  order_id, duration_sec, agent_tag="BOT"})`. La fila queda en scan_candidates
  con order_id → el UPDATE de resultado funcionará por order_id.
- Registrar también la orden en un registro de pendientes (p.ej.
  `EdificioContratacion.sent_orders[order_id] = {asset, direction, amount, payout,
  order_ref, sent_at, duration_sec, resolved=False}`).

**F2 — Resolvedor por ticket** (nuevo `resolve_contratados(bot)` en
`edificio_executor.py`, llamado en `scanner.py` justo después de
`execute_contratados`):
- Por cada orden con `not resolved` y `now >= sent_at + duration_sec + 1`:
  `check_win(order_ref)` con `asyncio.wait_for` (timeout MARTIN_RESOLVE_TIMEOUT_SEC)
  + `_interpret_broker_result` — CRÍTICO: profit==0 NO es LOSS (lag del broker),
  se reintenta en el próximo ciclo.
- Resuelto → `record_order_result(order_id, outcome, profit)` (UPDATE por
  order_id en scan_candidates) + card: `order_status="won"/"lost"`, `reason`
  + append a la secuencia combinada.
- Máximo de intentos y retry: reusar MARTIN_RESOLVE_MAX_ATTEMPTS / RETRY_SEC.
- Preferir EXTRAER `_interpret_broker_result` a función compartida (o importarla
  de executor si no hay import circular) en vez de duplicarla.

**F3 — Secuencia combinada cronológica** (bug confirmado en `hub/server.py:231`):
- `"W"*wins + "L"*losses` agrupa W y L — Massaniello solo guarda contadores.
- Solución: `bot.outcome_history = deque(maxlen=200)` en `consolidation_bot.__init__`.
  - STRAT-F: append "W"/"L" en `_update_cycle_after_result` (executor.py:869).
  - Edificio: append en el resolvedor F2.
- `hub/server.py`: `"sequence": "".join(bot.outcome_history)` (hilo continuo, no
  se resetea con el ciclo — el usuario pidió un solo hilo cronológico).
- `hub/hub_models.py:155`: actualizar comentario del campo `sequence`
  (ya no es solo "del ciclo en curso").

### Archivos a tocar
`src/edificio_executor.py` (F1+F2), `src/edificio_contratacion.py` (sent_orders),
`src/scanner.py` (call a resolve_contratados), `src/consolidation_bot.py`
(outcome_history), `src/executor.py` (append STRAT-F; posible extracción de
_interpret_broker_result), `hub/server.py` (sequence), `hub/hub_models.py`
(comentario), `hub/static/index.html` (card muestra won/lost), tests
(test_edificio_executor, nuevo test resolvedor + secuencia).

### Tests
- F1: orden confirmada → fila en scan_candidates con strategy="EDIFICIO" y order_id.
- F2: WIN por check_win; LOSS; profit==0 → reintento (no LOSS); record_order_result
  actualiza la fila; card queda won/lost.
- F3: secuencia combinada en orden de llegada (STRAT-F + edificio intercalados).

### Implementación (hecha 2026-07-31)
- ✅ `src/edificio_contratacion.py`: `BuildingCard.order_ref`/`ContratadoEvent.order_ref`
  (ticket numérico); `EdificioContratacion._sent_orders` + `register_sent()`/`sent_pending()`.
- ✅ `src/edificio_executor.py`: F1 en `_send_one` (guardar order_ref + `_record_sent_to_black_box`
  con strategy="EDIFICIO" + registrar pendiente); F2 `resolve_contratados(bot)` +
  `_resolve_one` (check_win por ticket con wait_for, reintentos MARTIN_RESOLVE_*,
  UNRESOLVED sin forzar LOSS, UNA orden por llamada para no bloquear el loop).
- ✅ `src/connection.py`: `interpret_broker_result()` EXTRAÍDA (función compartida) —
  `executor.py::_interpret_broker_result` ahora delega (evita duplicación).
- ✅ `src/scanner.py`: `await resolve_contratados(self.bot)` tras execute_contratados.
- ✅ `src/consolidation_bot.py`: `self.outcome_history = deque(maxlen=200)` (hilo
  cronológico continuo, NO se resetea con el ciclo).
- ✅ `src/executor.py`: `_update_cycle_after_result` appendea W/L al historial.
- ✅ `hub/server.py`: `"sequence"` = `"".join(bot.outcome_history)` (reemplaza el
  bug `"W"*wins + "L"*losses` que agrupaba).
- ✅ `hub/hub_models.py` + `hub/static/index.html`: comentario actualizado; card
  muestra badge WIN ✓ / LOSS ✗.
- ✅ Tests nuevos `tests/test_edificio_trazabilidad.py` (10): 27 passed en los 3
  archivos de edificio; test_executor 3 fallos = baseline (verificado con stash).
- BUG propio detectado por tests y corregido: UNRESOLVED NO debe entrar a la
  secuencia ni marcar card (solo WIN/LOSS).

### Pendiente
- Commit (cuidado: NO incluir cambios ajenos del working tree: maturing_watcher.py,
  strat_fractal.py, start_webapp.bat, .atl/*, feature_list.json, runtime/main.lock).

---

## FIX: CONTRATADO → orden real al broker — 2026-07-31

### Síntoma (Ruben)
NZDCAD_otc aparecía "CONTRATADO" en el hub pero la orden nunca llegaba al broker.

### Causa raíz (auditoría)
El único consumidor de `pop_contratados()` era `_auto_contract_loop` (hub/server.py:436),
que SOLO se arranca dentro de `hub.server.run_server()`. El arranque real
(`start_webapp.bat → app.py → uvicorn.run(_hub_app)` en main()) nunca pasa por
`run_server` → el loop jamás corre. El import `run_server as _hub_run_server`
en app.py:102 existía pero estaba muerto. El activo quedaba clavado en piso 4
CONTRATADO para siempre (cada scan posterior: reason "P1 OK", stay).

### Fix aplicado
- NUEVO `src/edificio_executor.py`: `execute_contratados(bot)` consume la cola y
  envía la orden real con `place_order(client)` — socket único (regla de oro).
  Re-encola fallos con límite `EDIFICIO_MAX_ORDER_TRIES`; guard de trades abiertos.
- `src/scanner.py`: tras `_feed_edificio` → `await execute_contratados(self.bot)`;
  ahora calcula y pasa `cross_sticky` (filtro sticky antes muerto).
- `src/edificio_contratacion.py`: `ContratadoEvent` con `tries`/`order_id`/`order_status`;
  `BuildingCard.order_id`/`order_status`; método `requeue()`; expuestos en `get_state()`.
- `hub/server.py`: eliminado `_auto_contract_loop` (evita doble orden); endpoint
  manual `/api/contract/execute` ahora re-encola en fallo (no pierde el evento).
- `src/consolidation_bot.py` + `app.py`: logger `edificio_contratacion` conectado
  a la bitácora del bot y al ring del hub.
- `hub/static/index.html`: renderiza piso 4 (CONTRATADO) con estado de orden
  (enviada · id / falló / esperando envío).
- `src/config.py`: `EDIFICIO_ACCOUNT_TYPE=PRACTICE`, `EDIFICIO_ORDER_AMOUNT=1.0`,
  `EDIFICIO_ORDER_DURATION_SEC=900`, `EDIFICIO_MAX_ORDER_TRIES=2`,
  `EDIFICIO_STICKY_THRESHOLD=3.0`, `EDIFICIO_MAX_EVENT_AGE_SEC=120`.

### Gate de frescura (pedido Ruben, mismo día)
- Si el evento CONTRATADO espera más de `EDIFICIO_MAX_EVENT_AGE_SEC` (120s, p.ej.
  por trade abierto), NO se envía la orden obsoleta: `_expire_event` devuelve la
  card a P3 con POIs intactos para re-contratar con señal fresca.
- Hub: badge "esperando envío… Ns" con edad en vivo.
- Tests: +2 (expirado no envía y vuelve a P3; fresco dentro de ventana se envía).

### Tests
- `tests/test_edificio_contratacion.py` (8) + `tests/test_edificio_executor.py` (7):
  15 passed. Sin regresiones nuevas: 11+6 fallos de baseline idénticos con/sin fix
  (verificado por git stash).

### Pendiente
- ✅ REINICIO HECHO 2026-07-31 12:12:42 (app + servidor, ver sección MONITOREO).

### MONITOREO 1H POST-FIX (Ruben 2026-07-31) — DOCUMENTACIÓN DEL PROBLEMA
- **Problema documentado:** NZDCAD_otc "CONTRATADO" sin orden al broker (causa raíz
  arriba). Criterio de cierre: si en 1 hora (12:12 → 13:12) se envía la orden al
  broker → PROBLEMA SOLUCIONADO. Si continúa → buscar solución.
- **Línea de base (12:18):** 11 activos en edificio (10 P1, 1 P2), 0 contratados,
  0 órdenes con order_id en caja negra. Scans cada ~60s OK.
- **✅ RESULTADO: PROBLEMA SOLUCIONADO (12:32, a los ~20 min del arranque).**
  Primera orden enviada al broker con id confirmado:
  - 12:32:17 `[EDIFICIO] USDNGN_otc: ORDEN ENVIADA CALL $1.00 900s → id=88c35e84-…`
  - 12:35:18 `[EDIFICIO] XAGUSD_otc: ORDEN ENVIADA PUT $1.00 900s → id=bafdcc4b-…`
  - 12:36:15 `[EDIFICIO] XRPUSD_otc: ORDEN ENVIADA CALL $1.00 900s → id=80233e82-…`
  - 12:39:18 `[EDIFICIO] ETHUSD_otc: ORDEN ENVIADA PUT $1.00 900s → id=bb0ffe71-…`
  Flujo completo en vivo: P1 → P2 → P3 → CONTRATADO → ORDEN ENVIADA en el MISMO
  ciclo (~1-2s). Sin re-encolados, sin rechazos, sin señales expiradas.
- **Cierre (13:10, hora completa): 7 órdenes enviadas en total.** El proceso se
  reinició solo a las 12:56 (sin crash en log; probablemente cierre de ventana o
  relanzamiento manual) y el nuevo proceso volvió a operar correcto:
  - 13:04:30 XAGUSD_otc PUT → id=acb4ecf9-…
  - 13:09:36 LINUSD_otc PUT → id=29f512d3-…
  - 13:09:37 TONUSD_otc PUT → id=fcf29fb0-…
  Veredicto: **FIX CONFIRMADO en 2 procesos distintos, 0 fallos.**
- **Nota de trazabilidad (mejora futura):** las órdenes del edificio salen por
  place_order directo y NO quedan en scan_candidates (black box) ni en
  trade_journal.candidates (journal de hoy vacío). Su registro es solo el log
  `[EDIFICIO] ORDEN ENVIADA id=…`. Pendiente: registrar order_id en black box
  para trazabilidad de resultados WIN/LOSS a los 900s.
- **Rondas:** cada ~10 min, script `%TEMP%\opencode\monitor_edificio.py` (log +
  caja negra + hub API).

---

## AUDITORÍA SCANS NOCTURNOS 29→30 Jul — 2026-07-30 (tarde)
### Objetivo (Ruben)
Auditar por qué los scans de anoche (post-7PM Ecuador) no generaron entradas reales
a pesar de tener 128 ACCEPTED en black box. Verificar timezone, scores, y pipeline.

### Hallazgos

**TZ:** Broker UTC-3, Ecuador UTC-5. Midnoche broker = 22:00 Ecuador.

**Black box 2026-07-29.db (post-midnight broker = 19→00 Ecuador):**
- 688 REJECTED_STRAT_F (per-asset filters)
- 128 ACCEPTED (pasaron filtros per-asset) — TODOS con score=100.0 / confidence=0.0
- 119 ACCEPTED_NOT_ENTERED (pasaron select_best pero broker rechazó)
- 9 ACCEPTED (sin procesar aún)

**Causa raíz de score=100.0:** `f_eval.strength` siempre es 1.0 para cualquier patrón
que pasa per-asset filters (scanner.py L2576, L2650). STRAT-F no discrimina calidad
→ todos reciben score perfecto. Score_breakdown = compression:0 + fractal:35 + context:25 + payout:~20 = ~80 base, el resto de boosts.

**Causa raíz de 0 entradas:** 100% de candidatos son OTC. Quotex PRACTICE account
rechaza OTCs con reason=unexpected. El fix en L2073-76 itera alternativas pero todas
son OTC → mismo resultado. Las 16 entradas del log fueron de sesiones pre-7PM.

**Bot log noche: 44 scans, Entradas:16 (acumulado), Sin señal:249, Drawdown:-42.8%**

### Pendiente
- Investigar por qué `f_eval.strength` siempre da 1.0
- Solucionar entrada en PRACTICE con OTCs
- Decidir si atacar scorer o broker issue primero

## AUDITORÍA DE RECHAZOS + columna `band` — 2026-07-25 (tarde)
### Objetivo (Ruben)
Investigar mañana por qué el bot rechaza entradas y si los rechazos "zona muy
joven" luego se reusaron vía maturing watchlist. El agente que aprende debe
manejar mejor la estrategia. Estudio del estocástico centrado en la hora del
rechazo: 1 día antes + 3h después ("foto" del gráfico). Explicación técnica + dumi.

### Hallazgos previos (verificados en código/datos)
- Black box = scan_candidates (data/db/black_box_strat_*.db). STRAT-F SÍ graba
  rechazados; STRAT-A solo va a trade_journal. Foco en STRAT-F.
- 25-07: 17 REJECTED_STOCH + 1450 REJECTED_STRAT_F. Motivos típicos: "zona muy
  joven (2<3 velas M5)", "M1 no rechaza la banda", "M15 rango roto".
- MaturingWatchlist es EN MEMORIA y se borra al promover, PERO la promoción SÍ
  escribe en scan_candidates (SHADOW_PROMOTED / ACCEPTED). Clave = asset|dir|band.
- PROBLEMA: scan_candidates NO guarda `band` (nivel) -> cruce rechazo->promoción
  es aproximado. Solución: agregar columna `band` REAL y poblarla en STRAT-F.
- candles_15m solo trae 20 velas (~5h); para [-1d,+3h] hay que bajar por API demo
  (fetch_candles en connection.py). Activos rechazados son *_otc (no en parquet).

### Plan en curso
1. Subagente (deleg_7d378988, BACKGROUND) construye:
   - columna `band` en black_box_recorder.record_candidate (idempotente)
   - poblar `band` en scanner.py (REJECTED_STRAT_F joven, SHADOW_PROMOTED, ACCEPTED STRAT-F)
   - scripts/audit_rechazos.py (extract/download/analyze/report offline)
   - tests/test_audit_rechazos.py
2. CUANDO el subagente termine (confirmar ediciones + tests verdes), REINICIAR
   el sistema (start_webapp.bat) para que el bot acumule datos con `band` esta noche.
3. Mañana: solo investigar con scripts/audit_rechazos.py sobre datos acumulados.

### Estado
- Sistema vivo ahora: app.py PIDs 16768, 13448 + hub Edge. NO reiniciado aún
  (espero a que el subagente termine de editar el código).
- Watchdogs borrados (sesión previa): watchdog_quotex/bot/collect/hub + audusd +
  install_task_24x7. Quedan caffeine.py (keepalive) y app.py:_battery_watchdog.



## FIX: Cafeína (keepalive) + 24/7 — 2026-07-23

### Diagnóstico (por qué "la cafeína no funcionaba")
1. La caffeine NUNCA corrió en la instancia viva: el bot que corría arrancó ~08:57 y
   `src/caffeine.py` se creó a las 11:11. El proceso vivo era código viejo.
2. Al ponerle caffeine, el bot "se dormía" porque el PROCESO moría al cerrar la ventana
   cmd (no es idle del WS, es el server que cae al cerrar sesión). Mi lanzamiento
   desde la terminal de Hermes tampoco dejaba proceso vivo al cerrar.
3. Bug introducido: `basicConfig(force=True)` duplicaba el handler del log ->
   `PermissionError` (WinError 32) en rollover porque server + trader (2 procesos)
   abren `data/logs/runtime/consolidation_bot.log`.

### Cambios aplicados (verificados en vivo)
- `src/config.py`: CAFFEINE_INTERVAL_SEC=15, TICK_AFTER_IDLE_SEC=30 (era 20/45).
- `src/caffeine.py`: ya enviaba "2" (texto) + 42["tick"]; sin cambios de fondo.
- `src/consolidation_bot.py`: logger propio "consolidation_bot" + handler
  `_SafeRotatingFileHandler` (override rotate con reintento + copy/truncate para
  soportar 2 procesos en Windows). Logger "caffeine" conectado al mismo archivo.
- `scripts/watchdog_bot.py`: LOG_PATH corregido a `data/logs/runtime/consolidation_bot.log`;
  añadida `frequent_reconnects()` (14 reconexiones/600s) y `main()` convertido a bucle
  persistente (vigila 24/7 en un solo proceso).

### Verificación empírica
- Bot vivo (API state=running), caffeine arrancada: "☕ Caffeine arrancado — ping app
  cada 15s, tick tras 30s idle".
- 0 reconexiones WS en ~2 min con caffeine 15/30 (antes se reconectaba cada rato).
- Logger "caffeine" ya escribe a la bitácora.

### Pendiente 24/7 REAL (sin ventana abierta)
- Mi lanzamiento no deja el proceso vivo al cerrar sesión. Creado
  `install_task_24x7.bat` (schtasks /RU SYSTEM /SC ONSTART /RET 3 /RI 1) que arranca
  `run_bot_task.bat` (bot + watchdog) como tarea programada. REQUERE correr como
  ADMINISTRADOR. Hasta que el usuario lo corra, el bot vive solo mientras la sesión de
  Hermes esté abierta.
- El watchdog reparado revive el bot si Quotex lo desconecta (reconexiones frecuentes).

## Experimento spring_margin — Validación Wyckoff Fase C (STRAT-F)

### SPRING_EXPERIMENT_START
**2026-07-17T23:57:45Z** (UTC ISO 8601) = **2026-07-17T20:57:45-03:00** (formato
BROKER_TZ que guarda el bot en `scanned_at`, ver trade_journal._now()).
Todas las queries usan el formato **-03:00** (NO el Z) porque `scanned_at`
es TEXT con offset explícito y SQLite compara lexicográficamente:
`scanned_at >= '2026-07-17T20:57:45-03:00'`.
NO se borra ni trunca ninguna fila de trade_journal.db bajo ninguna
circunstancia; el filtro por scanned_at aísla el experimento.

Regla de columnas (verificado contra schema real):
- NO existe `created_at` → se usa `scanned_at` (TEXT ISO UTC, momento del
  escaneo en log_candidate).
- NO existe `duration_sec` → se usa `entry_duration_sec` (log_candidate
  recibe duration_sec y lo guarda ahí).

### Query de conteo FASE 1 (umbral 40 filas)
```sql
SELECT COUNT(*) FROM candidates
WHERE spring_margin IS NOT NULL
  AND outcome IN ('WIN','LOSS')
  AND entry_duration_sec = 300
  AND scanned_at >= '2026-07-17T20:57:45-03:00'
```

### Query de análisis FASE 2
```sql
SELECT spring_margin, outcome FROM candidates
WHERE spring_margin IS NOT NULL
  AND outcome IN ('WIN','LOSS')
  AND entry_duration_sec = 300
  AND scanned_at >= '2026-07-17T20:57:45-03:00'
```

Resto del protocolo igual: WIN/LOSS (excluye UNRESOLVED); NULL excluidos
del análisis y reportados aparte; umbral de decisión 8pp (bucket mayor
margen vs menor por >=8pp de win rate + correlación de signo consistente);
muestra mínima 30/grupo; umbral fijado ANTES de datos, no se ajusta.

---

## Feature completada: STRAT-F math filters + contextual scoring (2026-07-20)

### Qué se hizo
1. **P0-1**: M1 rejection ahora requiere 2 velas consecutivas (`_m1_rejects_band` en strat_fractal.py)
2. **P0-2**: Duración cambiada 600s → 900s (`config.py`: `DURATION_SEC`, `MULTI_DURATION_SECS`, `MULTI_DURATION_MASSANIELLO_PRIMARY_SEC`)
3. **P1-1**: Nuevo módulo `src/math_filters.py` — fractal dimension (Hurst), R² de regresión lineal, price vector angle (atan2), Bollinger squeeze, `compute_signal_quality` composite scorer
4. **P1-2**: Wyckoff band ahora es un rango (floor+ceil del fractal candle range), no precio único
5. **P1-3**: Stochastic zones V2 — `apply_stoch_help` ahora acepta `k_prev`/`d` keyword-only; vetos solo se activan cuando el cruce confirma reversión, momentum continuation = PASS
6. **P1-4**: `_m15_context` reemplazado por regresión (R² + slope angle) en vez de umbrales hardcodeados 0.004/0.006
7. **P2-1**: Scoring contextual de 3 niveles: proportional zones (sin dead zone) + weight M15 contextual (range=30%, trend=70%, broken=100%) + consensus bonus (3/4 → +0.05, 4/4 → +0.08)

### Archivos tocados
- `src/math_filters.py` (NUEVO)
- `src/strat_fractal.py` (modificado)
- `src/stochastic_zones.py` (modificado)
- `src/stochastic_m15.py` (modificado)
- `src/scanner.py` (modificado)
- `src/config.py` (modificado)
- `tests/test_stochastic_zones.py` (modificado)
- `tests/test_strat_fractal.py` (modificado)

### Tests
73 tests totales (60 strat_fractal + stochastic_zones). Todos verdes.

---

## Feature en curso
FIX RUNTIME — cuelgue por caída de WS durante espera de trade (multi-leg)

## Plan
Eliminar trade_client (2º instancia, Pitfall J CORRECTION) y reconectar en la
ruta de resolución/espera usando el mismo socket (bot.ensure_connection).

## Hecho
- Causa raíz: cada pierna multi-leg (60/300/600/900s) es TradeState aparte con
  tarea de resolución en background. El WS cae en la espera (idle-timeout de
  cliente fresco idle) y `_resolve_trade` reintenta 6× sobre socket muerto SIN
  reconectar → piernas clavadas en bot.trades → `wait_while_trade_open` congelado.
- `executor.py`: `_ensure_trade_client_alive` (cliente fresco/orden) →
  `_reconnect_if_needed(label)` que usa `bot.ensure_connection()` (mismo path del
  loop principal, serializado por `_RECONNECT_LOCK`). Se llama antes de cada orden
  y en CADA intento de `_resolve_trade`.
- `executor.py`: 4 llamadas `place_order(self.trade_client,...)` →
  `place_order(self.client,...)` (un solo socket).
- `loop_utils.py`: `wait_while_trade_open` hace `ensure_connection()` cada 15s.
- `consolidation_bot.py`: trade_client separado desactivado (orden usa client directo).
- Verificación: AST OK en 3 archivos; pytest módulos editados 40 passed
  (test_smart_order_place, test_multi_duration_entry, test_m1_micro_confirm,
  test_executor, test_wait_while_trade_open). Smoke empírico (sin trade en vivo):
  WS muerto → `_resolve_trade` reconecta (reconnects=1) y resuelve en vez de colgar.

## Estado
fix implementado + verificado (tests verdes). Pendiente validación en vivo.

## Nota
REGLA DE ORO PARA NO ROMPER DE NUEVO (guardar en HANDOFF): jamás reintroducir
trade_client / 2ª instancia de Quotex. Las órdenes van SIEMPRE por
enviar_orden(self.client) en el socket único del loop. Si el WS cae en espera,
reconectar vía bot.ensure_connection() en _resolve_trade y wait_while_trade_open,
NO crear cliente nuevo. El skill quotex-bot-runtime-debug (Pitfall J CORRECTION)
lo prohíbe explícitamente.

---

## Mejoras operativas (2026-07-17, fuera de la feature de bug)

1. **Arranque inmediato**: `consolidation_bot.py` ya NO espera un "despertador"
   antes del primer scan. Al conectar, arranca el loop y escanea de inmediato.
2. **Sin límite de 60 min**: `config.py` `SESSION_MAX_MIN = 0` → Massaniello
   NO corta la sesión a los 60 min; se reinicia solo por completitud
   (SESSION_AUTO_RESET_ON_COMPLETE) en modo continuo.
3. **Scan cada 1 min sin espera**: `config.py` `ALIGN_SCAN_TO_CANDLE = False`
   → cuando no hay trade abierto, el scan corre cada `SCAN_INTERVAL_SEC = 60`
   (con cuenta regresiva en la misma línea del log), no alineado al cierre de
   vela. Más profesional y usa recursos del PC.
4. **FASE 3 en paralelo (ProcessPool)**: ver feature `parallel_scan_fase3`
   (id 15, status done). Solo el bloque STRAT-F se evalúa en paralelo en 10
   workers (50% de 20 cores); STRAT-A intacto. Speedup 2.19x verificado por
   benchmark. El loop WS queda libre durante la evaluación.

---

## Feature completada: parallel_scan_fase3 (id 15, status: done, AUDITADA+CORREGIDA 2026-07-17)

- **T1** loop_utils: ProcessPool global 10 workers (cpu//2).
- **T2** consolidation_bot: init al arranque, shutdown en finally.
- **T3** scanner: `_evaluate_strat_f_serial(ctx) -> StratFEvalResult` (pura).
- **T4/T5** `_run_strat_f_parallel` aplica deltas al loop (caja negra,
  maturing, logs, candidates, reject_counts, batch, stats).
- **T6** exceptions → log.error + continue (no aborta ciclo).
- **T7** degradación a serial si no hay pool.
- **T8** 4 tests verdes + benchmark 2.19x (N=40).
- **T9** pytest feature 4 passed; módulos importan OK; sin fallos nuevos.
- ⚠ **AUDITORÍA EN VIVO (2026-07-17) detectó 2 bugs** que los tests unitarios no
  cubrían: (1) el dispatch `_run_strat_f_parallel` quedó tras el `return` de
  `_scan_phase_evaluate_assets` / en método equivocado → STRAT-F no se evaluaba
  (`STRAT-F ok=0` siempre); (2) `upsert_young` con dict posicional vs kw-only →
  `_apply_strat_f_result` ahora usa `**args`. Ambos corregidos y re-validados en
  vivo (`STRAT-F ok=1..5`/ciclo, 0 errores maturing).
- Documentación: specs/parallel_scan_fase3/{requirements,design,tasks}.md.

---

## Feature observacional: spring_confirmed (heurística, NO SSD)
2026-07-17 — logging acotado, SIN alterar decisión/dirección/score.

Objetivo: etiquetar cada señal STRAT-F aceptada con `spring_margin`
(REAL, decimal % en trade_journal.candidates) para correlacionar
después spring_margin vs outcome (WIN/LOSS) sin leer logs a mano.

- Campo en DB: **REAL** (decimal, puede ser negativo), NO INTEGER bool.
  Razón (cambio Fase 0, 2026-07-17): `spring_confirmed` bool estaba
  estructuralmente sesgado a 1/NULL por STRAT_F_ZONE_MIN_AGE=3 (el filtro
  de edad garantiza >=3 velas 5m post-fractal, con lo cual el mínimo post
  casi siempre >= band -> True). El float continuo da resolución real.
- Función auxiliar: **`_spring_heuristic_5m1m`** (nombre explícito de
  HEURÍSTICA, NO el StochasticSpringDetector real de SMC-SYSTEMS). No
  confundir en el futuro con el SSD validado.
  Regla: CALL (fractal_down) → margen = (min(low post-fractal) - band)/band*100.
  Positivo = no rompió suelo (spring más limpio). Negativo = rompió.
  PUT (fractal_up) → margen = (max(high post-fractal) - band)/band*100.
  Espejo. Sin velas suficientes → None.
- Punto de integración: `evaluate_strat_f` return (strat_fractal.py:314)
  + log `[STRAT-F] ✓ spring_margin=` (scanner.py:2415) + `_rec` dict
  (scanner.py:2336) + `log_candidate` INSERT (trade_journal.py) + ALTER COLUMN.

### PLAN DE VALIDACIÓN WYCKOFF FASE C EN STRAT-F (fijado 2026-07-17)
Protocolo experimental con puertas de decisión. Hermes NO avanza de fase
sin confirmación explícita del operador.

- **FASE 0 — Corregir la métrica (BLOQUEANTE, hecha):** reemplazar
  spring_confirmed (bool) por spring_margin (float). Alcance: 4 archivos
  (strat_fractal.py, scanner.py, trade_journal.py, tests). Prohibido tocar
  if de aceptación/rechazo o score. Puerta: tests verdes + smoke DB con
  decimales reales (NO solo 1/0/NULL). ✅ COMPLETADA (commit pendiente).

- **FASE 1 — Recolección en demo (sin análisis):** correr bot en demo con
  spring_margin logueándose en cada señal STRAT-F aceptada. Hasta >=40
  filas con outcome resuelto (WIN/LOSS, excluyendo UNRESOLVED) y
  spring_margin no-NULL. Regla dura: NADIE mira la tabla antes de 40.
  Hermes reporta SOLO el conteo de filas, no win rate parcial.
  **FILTRO DURACIÓN (corregido 2026-07-17):** el usuario corre múltiples
  duraciones en paralelo (60/300/600/900s). El experimento spring_margin
  SOLO cuenta `entry_duration_sec = 300` (leg principal 5min). Las otras
  duraciones se guardan igual en la DB pero NO cuentan para el umbral ni
  el análisis. NOTA: la columna NO es `duration_sec` (no existe); es
  `entry_duration_sec` (log_candidate recibe `duration_sec` y lo guarda
  ahí). Query:
  `SELECT COUNT(*) FROM candidates WHERE spring_margin IS NOT NULL`
  `AND outcome IN ('WIN','LOSS') AND entry_duration_sec = 300`.
  Puerta: esa query >= 40.

- **FASE 2 — Análisis (una vez, criterio fijado en Fase 0):**
  1. Correlación (Pearson/Spearman) entre spring_margin y resultado binario
     (1=WIN, 0=LOSS).
  2. Buckets: 3-4 rangos de spring_margin (negativo / ~0 / amplio) y win
     rate por bucket.
  Criterio de decisión (FIJADO AHORA): si el bucket de MAYOR margen supera
  al de MENOR por >=8pp de win rate, Y la correlación tiene signo
  consistente con la hipótesis (margen mayor → más wins) → Fase 3A.
  Si no → Fase 3B (no-go). Nadie ajusta el umbral de 8pp después de ver
  los números.

- **FASE 3A — GO: portar SSD** (solo si Fase 2 confirma). Portar
  StochasticSpringDetector de smc_successer (SMC-SYSTEMS), NO reconstruir.
  Feature SDD completa: specs/<feature>/{requirements,design,tasks}.md +
  aprobación humana antes de código (AGENTS.md). Integración ya identificada:
  evaluate_strat_f ~línea 255 antes del return. Validación antes de vivo:
  walk-forward o repetir Fases 0-2 con el detector real en modo observacional
  antes de dejarlo decidir aceptación/rechazo.

- **FASE 3B — NO-GO: cerrar y documentar** (si Fase 2 no confirma).
  Documentar en progress/history.md que Fase C no mostró edge medible con
  esta muestra, con números exactos. NO se destruye spring_margin (campo
  observacional pasivo, útil con más volumen/otro activo). Redirigir esfuerzo
  al defecto ya identificado: gate m1_micro_confirm (una sola vela, sin
  magnitud mínima del movimiento en contra).

### PROTOCOLO DE ANÁLISIS (umbral fijado ANTES de datos — 2026-07-17)
- **Umbral para portar SSD**: bucket de mayor spring_margin supera al de
  menor por >=8pp de win rate, con correlación de signo consistente.
- **Muestra mínima por grupo**: 30 registros.
- **spring_margin IS NULL**: excluidos del análisis, reportados aparte.
- NO se ajusta el umbral según lo que salga. Esto está fijado.

---

## Feature #16 — Re-chequeo M15 al promover desde maturing_watchlist (STRAT-F)

**Estado:** DONE (2026-07-19). Feature SDD: `specs/strat_f_maturing_m15_recheck/`
(requirements.md / design.md / tasks.md). Aprobada y aplicada.

### Problema (raíz confirmada por auditoría)
El bot entraba en contra de la tendencia M15 visible (~30% de las operaciones
aceptadas, 13/43 en el audit). Causa: `evaluate_strat_f` tiene el filtro R1
(`if ctx=="downtrend" and direction=="CALL": skip`) pero la **sala de espera**
(`maturing_watchlist`) promueve zonas usando el `m15_context` de CUANDO se
detectó la zona, NO el actual. Si la tendencia viró mientras la zona maduraba,
la entrada sale contra-tendencia sin re-chequeo.

### Solución (tu teoría de agotamiento, aplicada donde filtra)
Al promover desde maturing_watchlist se re-evalúa el M15 ACTUAL:
- Alineado → promueve (R1/R5).
- Contra-tendencia → SOLO promueve si el **stoch M5** confirma agotamiento del
  contra-movimiento (CALL contra-M15-bajista → stoch M5 %K < 20; PUT
  contra-M15-alcista → stoch M5 %K > 80). Si no hay confirmación → **DROP**
  (no opera, R4). No consume Massaniello (el buy() real es el que consume).

### Archivos tocados
- `src/strat_fractal.py`: `recheck_m15_alignment()` + `stoch_m5_exhausted()`
  (funciones puras).
- `src/scanner.py`: import de las 2 funciones; re-chequeo en el bloque de
  promoción `mark_promoted`; `stoch_m15 = None` al inicio del bloque F (repara
  bug preexistente: `UnboundLocalError` con `_eval_override`).

### Tests
- `tests/test_strat_f_maturing_recheck.py` — 13 passed (R1-R5): recheck
  alineado/contra-tendencia, stoch exhaust/none, integración promoter-vs-drop.
- Suite completa: 21 failed pre-existentes (sin cambio vs baseline), 521 passed
  + 13 nuevos. Sin regresiones introducidas.

---

## FIX INFRA — Caffeine (keepalive de APLICACIÓN) — 2026-07-22

### SÍNTOMA (reporte usuario)
El bot "se duerme" si lo dejan mucho tiempo solo → "Connection to remote host
was lost". El usuario sospechaba que el módulo de reactivación ("cafeina") no
llegaba a tiempo. No había ningún módulo keepalive propio escrito.

### DIAGNÓSTICO (empírico, no suposición)
- `src/connection.py` solo reconecta DE MANERA REACTIVA (ensure_connection en
  top del loop / tras excepción). Nada envía "estoy vivo" en idle.
- pyquotex configura el WebSocket con `ping_interval=24, ping_timeout=20,
  ping_payload="2"` (api.py:454). SUENA bien...
- ...pero websocket-client 1.9.0 manda ese "2" como **ping frame binario**
  (`WebSocket.ping()` → `send(payload, ABNF.OPCODE_PING)`). Confirmado leyendo
  el código fuente de la librería instalada en `.venv`.
- Quotex habla **engine.io v3 / socket.io**: el keepalive de app es el mensaje
  de **TEXTO** "2", no un ping frame. El servidor ignora el golpecito binario.
- Respaldo de pyquotex roto en idle: `on_pong` manda "2" de texto, pero el
  servidor no responde pong al ping frame binario → on_pong nunca corre.
  `on_message` manda `42["tick"]` solo si un mensaje cae justo en segundos
  múltiplos de 5 → en idle real no pasa.
- Resultado: en inactividad (espera de vela 146s, entre scans) nadie le manda
  "2" de texto al server → Cloudflare cierra por idle → "se duerme".

### SOLUCIÓN
Creé `src/caffeine.py`: `CaffeineLoop` que cada `CAFFEINE_INTERVAL_SEC` (20s,
con jitter) manda el **TEXTO** "2" por `client.websocket.send()` (engine.io
ping de app), y además un `42["tick"]` si lleva rato sin tráfico de ENTRADA del
servidor (`CAFFEINE_TICK_AFTER_IDLE_SEC=45s`). Comparte `_RECONNECT_LOCK`
(RT-02) para no mandar tráfico mientras otra ruta reconecta. Engancha
`mark_traffic()` al on_message de pyquotex para medir inactividad real.

### CABLEADO (call sites reales — no queda muerto)
- `src/consolidation_bot.py`:
  - import `from caffeine import CaffeineLoop, install_traffic_hook`.
  - tras arrancar `_hub_sync`, crea `bot._caffeine = CaffeineLoop(...)` +
    `asyncio.create_task(bot._caffeine.run(), name="caffeine")` + instala hook.
  - en el `finally` del loop 24/7: `bot._caffeine.stop()` + cancela la task
    limpio antes de cerrar el client.
  - attrs inicializados en `__init__`: `self._caffeine_task`, `self._caffeine`.
- `src/config.py`: parámetros `CAFFEINE_ENABLED / _INTERVAL_SEC / _TICK_AFTER_IDLE_SEC / _JITTER_SEC`.

### TESTS (prueba de que el café llega en formato correcto)
`tests/test_caffeine.py` — 6 passed:
- el "2" se envía como TEXTO (opcode None), NO ping frame binario.
- maneja socket cerrado sin romper.
- loop manda ping periódico.
- loop manda `42["tick"]` tras idle.
- deshabilitado no manda nada.
- respeta `_RECONNECT_LOCK` (no envía mientras está tomado).

### NOTA ENTORNO (no introducida por este fix)
`tests/test_consolidation_bot.py` (6 tests) fallan por `numpy` no instalado en
`.venv` (pandas no importa) — deuda de entorno preexistente. `test_caffeine.py`
y `test_connection.py` pasan (21 passed). `consolidation_bot` importa OK.



