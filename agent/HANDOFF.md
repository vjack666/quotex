# HANDOFF — Session Transfer Document

> **Read this first** after `PROJECT_STATE.md` when resuming work.
> Last session: 2026-07-16/17 — stoch help, smart order, 24/7 Massaniello, scan 5m, quiet logs
> **Changelog:** `docs/CHANGELOG_2026-07-16.md`

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

---

## What remains (priority)

| Priority | Item | Owner |
|----------|------|-------|
| **P0** | Operar 24/7 con stoch hard + black box; validar impacto | Human + bot |
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
