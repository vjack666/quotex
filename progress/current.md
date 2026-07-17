# Estado de sesión

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

Objetivo: etiquetar cada señal STRAT-F aceptada con `spring_confirmed`
(INTEGER 1/0/NULL en trade_journal.candidates) para cruzar después
spring_confirmed vs outcome (WIN/LOSS) sin leer logs a mano.

- Campo en DB: **INTEGER** (1/0/NULL), NO TEXT. Razón: permitir
  `AVG(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)` directo por grupo.
- Función auxiliar: **`_spring_heuristic_5m1m`** (nombre explícito de
  HEURÍSTICA, NO el StochasticSpringDetector real de SMC-SYSTEMS). No
  confundir en el futuro con el SSD validado.
  Regla: CALL (fractal_down) → mínimo de candles_5m[i+1:i+4] vs band
  (low fractal). Si mínimo >= band → 1 (spring, no rompió suelo). Si
  rompió por debajo → 0. Si no hay velas 5m post-fractal suficientes
  (fractal_idx == last_idx), usar candles_1m recientes (mínimo 2-3).
  Si tampoco alcanza → NULL. Espejo para PUT (fractal_up, high fractal).
- Punto de integración: `evaluate_strat_f` return (strat_fractal.py:261)
  + log `[STRAT-F] ✓` (scanner.py:2411) + `_rec` dict (scanner.py:2330)
  + `log_candidate` INSERT (trade_journal.py) + ALTER COLUMN.

### PROTOCOLO DE ANÁLISIS (fijado ANTES de tener datos — 2026-07-17)
- **Umbral de decisión para portar SSD**: ≥8pp de mejora en win rate
  entre spring_confirmed=1 vs spring_confirmed=0.
- **Muestra mínima por grupo**: 30 registros (cada grupo debe tener ≥30).
- **Manejo de spring_confirmed=NULL** (sin velas suficientes para decidir):
  se EXCLUYEN del análisis de comparación 1-vs-0 (no cuentan como
  "no confirmado"). Se reportan aparte como "indeterminados".
- NO se ajusta el umbral de éxito según lo que salga. Esto está fijado.


