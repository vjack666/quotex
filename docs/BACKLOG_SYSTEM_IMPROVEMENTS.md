# Backlog — mejoras del sistema (fuera de STRAT-F)

> **Propósito:** guardar el inventario de módulos ya construidos y las mejoras
> que **quedaron pendientes** para endurecer el sistema global.
>
> **Foco actual del proyecto:** **STRAT-F** (datos en caja negra → análisis →
> estocástico en la entrada). Ver `docs/ROADMAP.md` Fase 6 y `agent/HANDOFF.md`.
>
> **No implementar desde este archivo** mientras el foco sea STRAT-F, salvo
> bug crítico que rompa la operación.

---

## Cómo usar este doc

| Si querés… | Hacé… |
|------------|--------|
| Seguir STRAT-F | Ignorá este archivo; usá `docs/ROADMAP.md` + black box |
| Planear mejora de sistema | Tomá un ítem de **Pendientes**, abrí SDD (`sdd: true`) y una sola feature |
| Recordar qué ya existe | Tabla **Inventario de sistemas** abajo |

---

## Inventario de sistemas (legacy roadmap + post-STRAT-F)

IDs de la columna “Feature” son del **roadmap global viejo** (pre–STRAT-F,
cerrado 2026-07-04), salvo nota. **No** confundir con IDs de `feature_list.json`
actual (STRAT-F #1–#8).

| Sistema | Feature (legacy) | Módulo / notas | Estado base |
|---------|------------------|----------------|-------------|
| Modular bot architecture | #1 | Facade + core (`consolidation_bot`, `scanner`, `executor`, …) | ✅ done |
| Strategy A (consolidation 5m) | #1, #17–#22 | `strat_a.py` + track quality/HTF/OB; radar `strat_a_radar.py` | ✅ done |
| Strategy B (Wyckoff spring/sweep) | #1 (legacy) | **ELIMINADA** 2026-07-11 — no reintroducir sin decisión explícita | ❌ removed |
| SMC analysis + decision engine | #2 | `smc_analysis`, `smc_decision_engine`, `smc_auto_trader` | ✅ done (stack invocable) |
| Entry scorer | pre-existing | Adaptive threshold en path de selección | ✅ done |
| Massaniello session manager | #16 | `massaniello_risk.py` — reemplaza martingale runtime | ✅ done |
| Parallel candle prefetch | #3 | `parallel_fetch.py` | ✅ done |
| Incremental candle cache | #4 | `candle_cache.py` | ✅ done |
| Entry sync precision | #5 | `EntrySynchronizer`; lag ≤ 0.3s | ✅ done |
| Strategy momentum 1m | #6 | `strat_momentum.py` | ✅ done |
| Strategy reversal swing | #7 | `strat_reversal_swing.py` | ✅ done |
| Strategy order block | #8 | `strat_order_block.py` | ✅ done |
| Backtesting engine | #9 | `backtester.py` — grid-search multi-origen | ✅ done |
| Dynamic weight calibration | #10 | `weight_calibrator.py` — Sharpe | ✅ done |
| Massaniello persistence | #11 | `massaniello_persistence.py` — SQLite | ✅ done |
| Hub live WebSocket | #12 | FastAPI + WS (`hub/server.py`, static UI) | ✅ done (+ panel STRAT-F) |
| Kelly criterion sizing | #13 | `kelly_sizer.py` — 25% fractional Kelly | ✅ done |
| Diversification enforcer | #14 | `diversification_enforcer.py` — límites configurables | ✅ done |
| Telegram alerts | #15 | `alerter.py` — eventos + cooldown | ✅ done |
| STRAT-A radar watchlist | ops | `strat_a_radar.py`; tick 1m top-5 | ✅ done |
| Test suite | all | `tests/` — mantener verde en env limpio | ⚠️ bankroll min_payout contamina suite |

### Añadidos posteriores (no estaban en la tabla legacy)

| Sistema | Notas | Estado |
|---------|-------|--------|
| STRAT-F (fractal M15/M5/M1) | `strat_fractal.py` + wiring scanner + hub | ✅ live (foco actual = datos/stoch) |
| Black box recorder | `black_box_recorder.py` + stoch M15 observado | ✅ midiendo |
| Hub bankroll Massaniello | capital / ops / ITM / payout desde UI | ✅ done |
| Schedule auto (Consola) | `schedule_controller`, `hub_schedule_store` | 🔄 impl lista; cierre formal pendiente |
| Duration live | `DURATION_SEC` sin import congelado | 🔄 review pendiente |

---

## Pendientes para mejorar el sistema

Prioridad relativa **dentro de este backlog** (no vs STRAT-F).  
`P1` = más útil cuando se retome el sistema global.

### P1 — Calidad y operación

| ID | Pendiente | Por qué importa | Área |
|----|-----------|-----------------|------|
| S1 | ~~**Aislar tests del bankroll**~~ | **done 2026-07-17** — `QUOTEX_TEST_MODE` + skip hydrate under pytest | tests / config |
| S2 | **Cierre formal** `schedule_auto` + review `duration_live` | Deuda de feature abierta en `feature_list.json` | hub / executor |
| S3 | **Validación live multi-estrategia** (A + momentum + swing + OB + F) con Massaniello | El roadmap viejo cerró por código; falta evidencia de sesión integrada | ops |
| S4 | ~~Rotación periódica de `consolidation_bot.log`~~ | **done 2026-07-17** — `RotatingFileHandler` 2MB×3 | ops |
| S0 | ~~Lifecycle X/Ctrl+C / single-instance~~ | **done 2026-07-17** — foreground bat + PID lock + hard-timeout cleanup + `stop_webapp.bat` | ops |

### P2 — Rendimiento y DRY

| ID | Pendiente | Por qué importa | Área |
|----|-----------|-----------------|------|
| S5 | `parallel_fetch` **DRY para order blocks** (prefetch OB unificado) | Menos I/O y menos caminos especiales en scan | `#3` / OB / scanner |
| S6 | Revisar hot path: `detect_order_blocks` / refresh sync en event loop | Ya hubo fixes de bloqueo; re-auditar bajo carga | scanner / executor |
| S7 | Caché / prefetch: métricas de hit-rate y techos de memoria | Evitar regresión de latencia al sumar TFs | `#3` `#4` |

### P3 — Inteligencia y sizing (ya existen; subutilizados o sin ciclo de mejora)

| ID | Pendiente | Por qué importa | Área |
|----|-----------|-----------------|------|
| S8 | **Ciclo de calibración** de pesos (`weight_calibrator`) con datos reales de journal | Hoy el módulo existe; falta ritual de recalibrar y aplicar | `#10` |
| S9 | **Kelly en producción**: validar que el stake hub/Massaniello y Kelly no peleen | Dos fuentes de sizing confunden bankroll | `#13` / hub |
| S10 | Diversification enforcer: revisar límites por activo/estrategia con STRAT-F only vs multi | Con F only los límites pueden ser irrelevantes o demasiado estrictos | `#14` |
| S11 | Backtester: escenarios STRAT-A/F + regresión de expectancy post-cambio de filtros | Evitar “mejoras” sin baseline | `#9` |
| S12 | Entry scorer: re-tune threshold con post-STRAT-F distributions | Threshold viejo puede sesgar multi-origen | scorer |

### P4 — Alertas, hub y SMC

| ID | Pendiente | Por qué importa | Área |
|----|-----------|-----------------|------|
| S13 | Telegram alerts: cobertura de eventos nuevos (session end, UNRESOLVED, schedule rest) | Ops real-time incompleta | `#15` |
| S14 | Hub: unificar paneles (STRAT-F + bankroll + schedule + black box) sin ruido | UX operador | hub |
| S15 | SMC stack: decidir si se integra al scanner o queda tool offline | Hoy es stack paralelo; documentar o cablear | `#2` |
| S16 | Strategy B: **no restaurar** salvo decisión de producto; si se necesita Wyckoff spring, SDD nuevo (no revivir archivos borrados a ciegas) | Evitar regresión de scope | — |

### Explicitamente NO son “pendientes de sistema” (van por STRAT-F)

| Tema | Dónde vive |
|------|------------|
| Recolectar black box + analizar `stoch_m15` | `docs/ROADMAP.md` Fase 6 |
| SDD de veto/boost estocástico en entrada | Tras datos; feature nueva STRAT-F |
| Filtros de calidad STRAT-F ya shippeados | Features #1–#7 done |

---

## Orden sugerido cuando se retome (después de STRAT-F data/stoch)

```
S1 tests limpios
  → S2 cierre schedule_auto / duration_live
    → S3 validación live multi-estrategia
      → S5 DRY OB prefetch
        → S8–S12 ciclo inteligencia (calibración, Kelly, backtest, scorer)
          → S13–S15 alerts / hub / SMC
```

Cada ítem grande → **una** feature en `feature_list.json` con `"sdd": true` y aprobación humana.

---

## Referencias

| Doc | Rol |
|-----|-----|
| `agent/PROJECT_STATE.md` | Estado actual (foco STRAT-F) |
| `agent/HANDOFF.md` | Cómo retomar la sesión |
| `docs/ROADMAP.md` | Roadmap STRAT-F + Fase 6 stoch |
| `feature_list.json` | Features activas (STRAT-F era + schedule_auto) |
| `progress/history.md` | Bitácora de lo ya cerrado |
| `docs/architecture.md` | ⚠️ puede estar desactualizado vs este backlog; no confiar ciegamente en “pendiente #N” viejos |

---

## Changelog de este archivo

| Fecha | Cambio |
|-------|--------|
| 2026-07-15 | Creación: inventario legacy + pendientes de sistema; foco STRAT-F fuera de alcance aquí |
