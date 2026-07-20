# Estado de sesión

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


