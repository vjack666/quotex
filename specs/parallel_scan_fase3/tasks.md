# Tasks — parallel_scan_fase3

Estado: COMPLETO (todas las tareas cerradas, tests verdes, benchmark PASS).

Decisión de diseño (OPTION 1, confirmada por el usuario): solo el bloque
STRAT-F (scanner.py ~1240-1473) se extrae a función pura y se evalúa en
paralelo vía ProcessPool. STRAT-A y el resto del `for` quedan intactos.

- [x] T1 — `src/loop_utils.py`: `init_scan_pool()` / `get_scan_pool()` /
      `shutdown_scan_pool()` gestionan un `ProcessPoolExecutor` global de
      `max(1, os.cpu_count()//2)` workers (10 en esta máquina de 20 cores).
      Cubre: R2.
- [x] T2 — `src/consolidation_bot.py`: `init_scan_pool()` al arranque (tras
      conectar) y `shutdown_scan_pool()` en el `finally` del loop. Cubre: R2, R4.
- [x] T3 — `src/scanner.py`: extraer el bloque STRAT-F a la función pura
      module-level `_evaluate_strat_f_serial(ctx: StratFEvalContext) ->
      StratFEvalResult` (sin `self`/`bot`/`executor`). Deltas en vez de
      mutaciones: candidates, reject_counts, strat_f_batch, stats, black_box,
      maturing_ops, logs. Cubre: R1, R3, R6.
- [x] T4 — `_scan_phase_evaluate_assets`: acumular `StratFEvalContext` por
      activo en `pending_f_ctxs` (el STRAT-A tail y el resto del `for`
      quedan igual) y, tras el `for`, llamar `_run_strat_f_parallel(...)` que
      aplica los deltas al loop. Cubre: R1, R4, R5.
- [x] T5 — `_run_strat_f_parallel` aplica los deltas (caja negra, maturing,
      logs, candidates, reject_counts, batch, stats) idénticos al original.
      Cubre: R1, R3.
- [x] T6 — Manejo de excepciones: `asyncio.gather(..., return_exceptions=True)`;
      por cada excepción `log.error` y `continue` (el ciclo no aborta).
      Cubre: R5.
- [x] T7 — Degradación: si `get_scan_pool()` es `None` (test mode / sin
      pickle), `_run_strat_f_parallel` evalúa serial `[_evaluate_strat_f_serial(c)
      for c in ctxs]`. Cubre: R6.
- [x] T8 — `tests/test_parallel_scan_fase3.py`: 4 tests verdes
      (función pura acepta/rechaza + dispatch serial aplica deltas + dispatch
      pool maneja excepción). `scripts/bench_parallel_scan_fase3.py`: speedup
      2.19x (serial 0.421s vs pool 0.192s, N=40, 10 workers). DoD R7 PASS.
      Cubre: R3, R5, R6, R7.
- [x] T9 — `pytest tests/test_parallel_scan_fase3.py` → 4 passed.
      Módulos editados importan OK (scanner / loop_utils / consolidation_bot).
      No se introdujeron fallos nuevos; los 12 fallos pre-existentes en
      test_scanner / test_scanner_strat_a / test_maturing_watchlist_scanner /
      test_strat_f_golive / test_massaniello_persistence son anteriores a esta
      feature y no están en su alcance. Cubre: R1-R7.
