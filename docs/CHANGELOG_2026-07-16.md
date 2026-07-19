# Changelog — 2026-07-16 / 2026-07-17

Documentación de cambios operativos y de producto aplicados en esta ventana de trabajo.
Para specs formales ver `specs/<feature>/`. Para handoff vivo ver `agent/HANDOFF.md`.

---

## Resumen ejecutivo

| Área | Cambio | Impacto |
|------|--------|---------|
| STRAT-F entrada | Stoch M15 como capa de ayuda (hard) | Veto/boost sin tocar el fractal |
| Place-order | Prewarm + reintentos + feedback hub | Menos “no hace nada” en timeouts |
| Ciclo Massaniello | Solo reset; bot no para | 24/7 recolección de data |
| Escaneo | Alineado al open de vela **5m** | Un ciclo por vela M5 |
| Orden buy/sell | Sync al open de vela **5m** (no 1m) | Entrada en estructura M5 |
| Logs | Countdown 1 línea; silencio con trade abierto | Consola legible |
| UX trade abierto | No scan / no spam; solo espera | CPU y log limpios |
| Place-order | Gate M1 micro-trend (default ON) | Bloquea CALL/PUT solo si M1 va claramente en contra |

---

## 0. `m1_micro_confirm` — pre-buy M1 micro-trend gate (default ON)

### Qué
Tras el sync de timing y el prewarm, y **antes** de `place_order`, se refrescan velas M1
y se aplica `confirm_m1_micro` (puro, sin I/O). Solo bloquea cuando la última M1 va
claramente en contra: CALL si close&lt;open y close&lt;prev_close; PUT si close&gt;open y
close&gt;prev_close. Datos insuficientes o fallo de fetch → **fail-open**. Multi-leg
siguientes no re-chequean (la primera pierna ya pasó el gate).

### Config
```text
M1_MICRO_CONFIRM_ENABLED = True
```

### Archivos
| Path | Rol |
|------|-----|
| `src/m1_micro_confirm.py` | Lógica pura |
| `src/executor.py` | `_m1_micro_confirm_pre_buy` + cableado en `enter_trade` |
| `src/config.py` | Flag default ON |
| `tests/test_m1_micro_confirm.py` | Unit + wiring |

---

## 1. `stoch_entry_help` (feature #9) — **done**

### Qué
Capa de ayuda del estocástico M15 sobre señales STRAT-F ya formadas.

### Comportamiento
- Zonas por %K: Z1 (0–20) … Z5 (80–100).
- **hard** (default): CALL+Z5 o PUT+Z1 → veto (`stoch_extreme_against`); extremos a favor → boost (+10/+5).
- **soft**: solo boost; **off**: solo medición.
- `evaluate_strat_f` **no se modifica**.

### Config
```text
STOCH_HELP_MODE=hard   # env: off | soft | hard
```

### Archivos
| Path | Rol |
|------|-----|
| `src/stochastic_zones.py` | Matriz pura zone/action/score_delta |
| `src/stochastic_m15.py` | Cálculo stoch (existente) |
| `src/scanner.py` | Wire post–`compute_stoch` |
| `src/config.py` | `STOCH_HELP_MODE` |
| `specs/stoch_entry_help/` | SDD |
| `tests/test_stochastic_zones.py` | Unit + config default |
| `tests/test_stoch_entry_help_scanner.py` | Integración scanner |
| `progress/impl_stoch_entry_help.md` | Trazabilidad R→test |

### Black box
`stoch_m15` JSON incluye `zone`, `action`, `score_delta` (+ campos de medición).

---

## 2. `smart_order_place` (feature #10) — **done**

### Qué
Colocación de orden más resiliente y visible.

### Comportamiento
1. **Prewarm** de `trade_client` durante/antes del wait al open 1m.
2. Reintentos de candidatos alternativos con `skip_open_wait` si el lag aún sirve.
3. Razón real de rechazo en log (timeout / unexpected / connection).
4. Hub: `last_order_attempt` (asset, direction, status, reason, ts).
5. Cuarentena de fallos duros: `ORDER_FAIL_QUARANTINE_CYCLES = 5`.

### Archivos
| Path | Rol |
|------|-----|
| `src/executor.py` | Prewarm, skip_open_wait, last_order_attempt |
| `src/scanner.py` | Loop de alts + razón real |
| `src/config.py` | `ORDER_FAIL_QUARANTINE_CYCLES` |
| `hub/server.py` | Expone attempt en state |
| `hub/static/index.html` | “Último intento” |
| `specs/smart_order_place/` | SDD |
| `tests/test_smart_order_place.py` | Cobertura |
| `progress/impl_smart_order_place.md` | Impl report |

---

## 3. Continuación 24/7 — solo reset Massaniello

### Qué
Al cerrar un ciclo Massaniello (meta ITM, timeout, exhausted, failed):
- **Solo** se resetea Massaniello (contadores limpios).
- El bot **sigue** escaneando/operando.
- **No** modal de “sesión finalizada → STOPPED”.
- **No** hace falta pulsar Iniciar.

### Config
```text
CONTINUOUS_DATA_COLLECTION_MODE = True
SESSION_AUTO_RESET_ON_COMPLETE = True
```

### Comportamiento técnico
- `executor._maybe_stop_massaniello_session` en auto-continue:
  - `session_stop_hit = False`
  - `bootstrap_for_run(..., force_new=True)`
  - evento suave `session_cycle_rolled` (`auto_continue: true`)
  - log: `♻️ Massaniello reset — ciclo cerrado (...); bot continúa sin parar`
- BotRunner pasa `continuous_mode=True` desde config.

### Archivos
| Path | Rol |
|------|-----|
| `src/executor.py` | `_auto_continue_enabled`, rama auto vs legacy |
| `src/config.py` | Defaults ON |
| `src/consolidation_bot.py` | `continuous_mode` desde config / BotRunner |
| `hub/static/index.html` | Toast cycle rolled; no modal si auto_continue |
| `tests/test_session_lifecycle.py` | Auto vs classic |
| `progress/impl_massaniello_reset_continue.md` | Impl |
| `progress/impl_continuous_24_7.md` | Impl paralelo (mismo producto) |

### Nota
Guardrails de continuous (racha de pérdidas, límite diario) **siguen**; solo se quitó el stop por fin de ciclo Massaniello.

---

## 4. Escaneo alineado a vela 5m

### Qué
El loop principal dispara **justo en el open** de la vela de 5 minutos.

### Config
```text
ALIGN_SCAN_TO_CANDLE = True
SCAN_LEAD_SEC = 0.0
```

### Lógica (`seconds_until_next_scan`)
- `phase == 0` (exact open) → wait `0` (escanear ya).
- Mitad de vela → wait hasta el próximo open.
- Corregido bug: con lead=0 en el open ya no saltaba 300s al *siguiente* open.

### Archivos
| Path | Rol |
|------|-----|
| `src/config.py` | Flags |
| `src/loop_utils.py` | `seconds_until_next_scan` |
| `src/consolidation_bot.py` | Label “Sincronizando open vela 5m” |
| `tests/test_scan_align_5m.py` | 6 tests |
| `progress/impl_scan_align_5m.md` | Impl |

---

## 4b. Orden buy/sell sincronizada al open 5m

### Qué
`EntrySynchronizer` ya no espera el open de vela **1m**. La orden se dispara en el open de la vela de entry TF (`ENTRY_SYNC_TF_SEC = TF_5M = 300`).

### Config
```text
ENTRY_SYNC_TF_SEC = TF_5M   # 300; legacy 1m = 60
ENTRY_SYNC_TO_CANDLE = True
ENTRY_MAX_LAG_SEC = 0.3
ENTRY_REJECT_LAST_SEC = 2.0
```

### Comportamiento
- `phase == 0` → wait 0, usa open actual (no salta al próximo).
- Decisiones: `SYNCED_ENTRY_OPEN` / `REJECT_LATE_ENTRY`.
- `skip_open_wait` en executor usa `entry_sync.tf_sec`.

### Caveat
Si scan+eval terminan después del phase 0 de la vela 5m, la orden espera el **próximo** open 5m (hasta ~5 min). Correcto para “exactamente en el open”.

### Archivos
| Path | Rol |
|------|-----|
| `src/config.py` | `ENTRY_SYNC_TF_SEC` |
| `src/entry_sync.py` | TF parametrizado + exact open |
| `src/executor.py` | skip_open_wait + snapshot `entry_sync_tf_sec` |
| `tests/test_entry_sync.py` | 5m + phase==0 |
| `progress/impl_entry_sync_5m.md` | Impl |

---

## 5. Log countdown de una sola línea

### Qué
El “Próximo escaneo en Ns” ya no spamea una línea por segundo.

### Comportamiento
1. **Una** línea durable al inicio: `⏳ {label} | wait=Ns`
2. En TTY: reescribe la misma línea con `\r` (solo números).
3. Sin `log.info` por segundo (no contamina `consolidation_bot.log`).

### Archivos
| Path | Rol |
|------|-----|
| `src/loop_utils.py` | `sleep_with_inline_countdown` |
| `tests/test_loop_utils_countdown.py` | Sin spam |
| `progress/impl_countdown_log.md` | Impl |

---

## 6. Silencio con trade abierto

### Qué
Con orden enviada / posición abierta:
- **No** se escanea.
- **No** se imprimen SCAN#, STATS, MASSANIELLO, “próximo escaneo”.
- Solo: espera a finalizar el trade.

### Comportamiento
1. Inicio: `⏳ En espera de finalizar trade | {asset} {DIR} ~Ns`
2. TTY: countdown en una línea.
3. Fin: `✅ Trade finalizado — reanudando escaneo`
4. WIN/LOSS al resolver se mantienen.

### Archivos
| Path | Rol |
|------|-----|
| `src/loop_utils.py` | `wait_while_trade_open` |
| `src/consolidation_bot.py` | Wait + `continue` (pre y post scan) |
| `src/scanner.py` | Early return **antes** del banner SCAN# |
| `src/executor.py` | Wait de liquidación → `log.debug` |
| `tests/test_wait_while_trade_open.py` | 3 tests |
| `progress/impl_quiet_trade_wait.md` | Impl |

---

## Features en `feature_list.json`

| ID | Name | Status |
|----|------|--------|
| 1–7 | STRAT-F + hub panel | done |
| 8 | `schedule_auto` | **in_progress** (pausado) |
| 9 | `stoch_entry_help` | **done** |
| 10 | `smart_order_place` | **done** |

Cambios ad-hoc (sin ID de feature): 24/7 Massaniello, align 5m, countdown log, quiet trade wait,
multi-duration data collection (1 señal → 4 expiries).

---

## 7. Multi-duration data collection (ad-hoc)

### Qué
Cada señal de entrada coloca **4 órdenes** en paralelo con expiries:
- 60s (1m), 300s (5m), 600s (10m), 900s (15m)

Objetivo: medir qué duración rinde mejor con STRAT-F (y el resto de orígenes).

### Comportamiento
1. Monto Massaniello se calcula **una** vez.
2. Sync de open en la primera pata; las demás usan `skip_open_wait`.
3. `bot.trades` se indexa por `asset#duration_sec` (no se pisan entre sí).
4. Black box: fila por duración (`duration_sec` INTEGER); **WIN y LOSS** resuelven `order_result`.
5. Massaniello / continuous / cycle / `_maybe_stop` solo en la pata primaria (**300s**).
6. Con `MULTI_DURATION_DATA_COLLECTION=False` el path single-duration se mantiene.

### Config
```text
MULTI_DURATION_DATA_COLLECTION = True
MULTI_DURATION_SECS = (60, 300, 600, 900)
MULTI_DURATION_MASSANIELLO_PRIMARY_SEC = 300
MAX_CONCURRENT_TRADES = 4  # cuando multi está on
```

### Archivos
| Path | Rol |
|------|-----|
| `src/config.py` | Flags multi-duration + concurrent caps |
| `src/models.py` | `make_trade_key`, `TradeState.trade_key` |
| `src/executor.py` | trade_key, `enter_multi_duration`, primary-only Massaniello |
| `src/scanner.py` | Multi entry + BB clone por duration |
| `src/black_box_recorder.py` | Columna `duration_sec` + clone |
| `src/diversification_enforcer.py` | Cuenta por `TradeState.asset` |
| `src/loop_utils.py` | Summary con duration |
| `tests/test_multi_duration_entry.py` | Unit coverage |
| `progress/impl_multi_duration_data.md` | Trazabilidad |

---

## Cómo operar después de estos cambios

1. **Reiniciar el bot** (parar e Iniciar) para cargar código y defaults.
2. Defaults relevantes:
   - `STOCH_HELP_MODE=hard`
   - `CONTINUOUS_DATA_COLLECTION_MODE=True`
   - `SESSION_AUTO_RESET_ON_COMPLETE=True`
   - `ALIGN_SCAN_TO_CANDLE=True` / `SCAN_LEAD_SEC=0`
3. Apagar stoch help: env `STOCH_HELP_MODE=off`.
4. Volver al “parar al fin de ciclo”: poner ambos flags continuous/auto-reset en `False` (requiere redeploy/restart).

---

## Pendiente (no hecho en esta ventana)

| Item | Notas |
|------|--------|
| Gate M1 micro-tendencia pre-buy | ✅ implementado ON (`M1_MICRO_CONFIRM_ENABLED=True`, `src/m1_micro_confirm.py`) |
| Stoch M1 timing | Opcional tras gate M1 |
| Cierre formal `#8 schedule_auto` | Review pendiente |
| Suite pytest bankroll `min_payout=90` | Known P1; `init.ps1` puede fallar |
| `duration_live` review formal | Impl previa pendiente reviewer |

---

## Engram (memoria persistente)

Topic keys relevantes en proyecto `quotex-hft-bot`:
- `sdd/stoch_entry_help/*`
- `architecture/stoch-entry-help`
- `bug/smart-order-place`
- `config/continuous-24-7`
- `ux/countdown-log`
- `ux/quiet-trade-wait`
- `bug/smart-order-place` (diagnosis + fix)

---

## Impl reports (detalle por cambio)

- `progress/impl_stoch_entry_help.md`
- `progress/impl_smart_order_place.md`
- `progress/impl_massaniello_reset_continue.md`
- `progress/impl_continuous_24_7.md`
- `progress/impl_scan_align_5m.md`
- `progress/impl_entry_sync_5m.md`
- `progress/impl_countdown_log.md`
- `progress/impl_quiet_trade_wait.md`
