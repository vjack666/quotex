# PROJECT_STATE

> Last updated: **2026-08-07** — Cierre definitivo del hilo del clustering (EXP-075 + EXP-074b-NULL).
> Freno científico aplicado: EXP-074b + EXP-075 NEGATIVOS; EXP-074b-NULL OOS colapsa.
> Full detail: `docs/CHANGELOG_2026-07-16.md` + `docs/LAB_CHARTER.md`

---

## 🔬 Laboratorio Científico (2026-08-06 tarde) — LEER PRIMERO al retomar

**Milestone actual:** Feature 38 `lab_protocolo_cientifico` = DONE. El lab evolucionó
de "buscar la vela ganadora" a MODELAR EL COMPORTAMIENTO DEL MERCADO (paradigma Wyckoff).

| Exp | Qué | Resultado | Commit |
|-----|-----|-----------|--------|
| EXP-071 | Zona Descubrimiento (contexto→confirmadores) | NINGÚN confirmador edge (FDR 0.018, EV neg) | efa212b |
| EXP-072 | Mapa de Transiciones (Markov estados) | mean-reverting; impulso se revierte (0.28-0.30); 0 estados favorable>0.55 | 76d467b |
| EXP-073 | Dinámica Fase A (energía, no eventos) | FDR 0/8: K-D no predice resolución; describe posición, no control | d696aba |
| EXP-074 | Clustering no supervisado Fases A | K=2 sil 0.2185 (24/76) — población mixta APOYADA | ca8035f |
| EXP-074b | Estabilidad de Clusters (freno, 6 pruebas) | RECHAZA GMM: no robusto a algoritmo/features/bootstrap. Lo real = duración continua | c4ecb42 |
| EXP-075 | Duración/Tipo Fase A como CONTINUA (re-enfoque 074b) | RESULTADO NEGATIVO: FDR 0/36, OR≈1.0, OOS plano. Duración NO predice resolución | pendiente |
| EXP-074b-NULL | Control nulo/surrogate + OOS temporal REAL | Veredicto: NO SOPORTADA. OOS colapsa (TEST 100% corto). Clustering = geometría del método | pendiente |

**Bloqueos (resueltos en 2026-08-07):** PRUEBA 3 OOS de EXP-074b YA se ejecutó (el
dataset EURUSD ahora llega a 2026, 3307 fases). TRAIN 2022-2024 / TEST 2025-2026.

**Conclusión de sesión:** el hilo del clustering (binario + continuo) quedó CERRADO. El
estocástico M15 describe ESTADO, no CONTROL ni transición. No se promueve nada al Edificio
(Art. 13). Matiz honesto: en EXP-074b-NULL el silhouette del null (0.405) > REAL (0.2185)
porque el null de shuffle de columnas es "fuerte" (geometría favorable); el veredicto se
apoya en la OOS (colapso total) y el %minoritario en el borde del null.

**Siguiente (PENDIENTE decisión A1/A2 Trader-Humano):** Energía Wyckoff BLOQUEADA por instrumento
(NO resultado negativo). EURUSD M15 = `tick_volume` 55% ceros. Candidato local Dukascopy M1
EVALUADO y RECHAZADO (99.7% ceros M15). FX spot OTC no tiene volumen centralizado; tick volume
de cualquier feed es disperso/cero. Diseño vivo en `hypothesis_energia_wyckoff_design.md` (BLOCKED).
`DATA_REQUIREMENTS_EW.md` actualizado con realidad FX y candidato rechazado. Conclusión: "Hipótesis
NO EVALUADA por insuficiencia del instrumento de medición". NO ejecutar EW-1/2/3; NO descargar.
- (A1) Evaluar SEGUNDO candidato: futuros CME EURUSD (volumen de bolsa real, aunque sea futuro no spot).
- (A2) Aceptar bloqueo de la vía (hipótesis no falseada). Sin OK no busco ni congelo nada.

**Tests:** pytest test_experiment_runner + test_promotion_gate + test_registry = 4 passed
(pre-existing; scripts lab_exp0XX NO están en la suite — se verifican por ejecución real).

---

## 🔬 Laboratorio Científico (2026-08-06 mañana) — Feature 38 base

**Milestone anterior:** Feature 38 `lab_protocolo_cientifico` = DONE y pusheada.
El bot ahora tiene un sistema de gobierno de hipótesis (Charter → spec → EXP).

| Capa | Archivo | Rol |
|------|---------|-----|
| Constitución | `docs/LAB_CHARTER.md` | Art.1–12 (FDR, Dominio, Parsimonia, Muerte definitiva) — inquebrantable |
| Manual | `docs/specs.md` | SDD + ciclo de vida científico + checklist Art.6/10/11/12 + Trader-Humano |
| Spec | `specs/lab_protocolo_cientifico/` | requirements/design/tasks/trader_humano_review (aprobado) |
| Plantillas | `docs/lab_templates/*.md` | hypothesis / risks / validation (con Effect Size + Costo) |
| ADR | `docs/decisions/ADR-001..004` | FDR, REAL/OTC, Dominio, Parsimonia/Muerte |
| Dataset | `datasets/dataset_v001/manifest.json` | versionado, referencia SMC_ROOT (sin copiar) |
| CLI | `scripts/lab_run.py` | `lab run EXP-XXX` (reproducible, congela protocolo) |
| CI | `scripts/lab_ci.py` + `.github/workflows/lab-ci.yml` | hash + reproducibilidad + FDR + reporte inmutable |
| Runner | `src/strategy_lab/experiment_runner.py` | reports inmutables (seed/env/hash/protocol/lifecycle) |

**Bloqueos:** ninguno de la feature 38. Próximo paso sugerido: aplicar el lab
al embudo roto del Edificio (EXP-039: 40→2→0→0; cuello = FRENO).

**Tests:** pytest test_experiment_runner + test_promotion_gate + test_registry
= 19 passed. `lab run` y `lab ci` GREEN sobre datos sintéticos.

---

## Project identity

| Field | Value |
|-------|-------|
| Name | quotex-hft-bot |
| Type | HFT binary options bot for Quotex |
| Language | Python 3.10+ (running 3.13/3.14) |
| Risk manager | **Massaniello** (ops / ITM / timeout / PRACTICE) |
| Strategy focus | **Edificio de Contratación** (ÚNICA activa — final, para REAL) |
| Roadmap | #1–#7 done; #9–#10 done; #11 done; #15 done; #16 done; #17 watchdog_bot done; #8 schedule_auto paused |
| Data collection | **24/7** — cycle end resets Massaniello only; `DAILY_LOSS_GUARD_ENABLED=False` en disco (sin freno diario) |

---

## Estrategias archivadas (etapa concluida — NO reactivar sin pedido del usuario)

| Estrategia | Estado | Nota |
|------------|--------|------|
| STRAT-A (consolidación 5m) | ✅ conclusa | Fue el primer paso hacia el Edificio — misión cumplida |
| STRAT-F (fractal + stoch M15) | ✅ archivada | Etapa concluida |
| STRAT-B, SMC y demás | ✅ archivadas | Etapa concluida |

> El **Edificio de Contratación** (`src/edificio_contratacion.py`) es la estrategia
> FINAL para operar en real. Todo el trabajo actual es sobre él.

---

## Current architecture

```
connection → scanner → strat_fractal + stoch_zones → executor
                         ↘ massaniello (auto-reset)
                         ↘ entry_sync / place_order prewarm
                         ↘ black_box
```

STRAT-F hot path:

```
prefetch 5m/1m/15m → evaluate_strat_f
  → R3 young + MATURING_WATCHLIST_MODE≠off → maturing_watchlist upsert
  → compute_stoch + apply_stoch_help (hard, V2 with k_prev/d)
  → compute_contextual_modifier (proportional + M15 weight + consensus)
  → mature re-eval: live→candidate / shadow→metrics only
  → candidate → Massaniello → enter_trade (prewarm + 1m sync)
  → if open trade: quiet wait (no scan)
  → resolve → next cycle
```

Watchdog (mantiene 24/7 sin intervención):

```
cron cada 5 min → watchdog_bot.py
  → API 127.0.0.1:8080 + proceso + marker "Connection to remote host was lost"
  → si cae O state≠running/starting → cleanup + reinicio + loop 24/7
  → log en scripts/watchdog.log
```

Scan cadence: **align to 5m candle open** (`ALIGN_SCAN_TO_CANDLE`, lead 0).

---

## Operational flags (defaults)

| Flag | Default | Meaning |
|------|---------|---------|
| `STOCH_HELP_MODE` | `hard` | Stoch help on entry |
| `CONTINUOUS_DATA_COLLECTION_MODE` | `True` | 24/7 path |
| `SESSION_AUTO_RESET_ON_COMPLETE` | `True` | Massaniello reset, no stop |
| `ALIGN_SCAN_TO_CANDLE` | `True` | Fire at M5 open |
| `SCAN_LEAD_SEC` | `0.0` | Exactly at open |
| `ORDER_FAIL_QUARANTINE_CYCLES` | `5` | Hard-fail asset skip |
| `MATURING_WATCHLIST_MODE` | `live` | off\|shadow\|live — R3 young watchlist |
| `MATURING_WATCHLIST_MAX_AGE_BARS` | `12` | Drop if still immature past this M5 age |
| `MATURING_WATCHLIST_TTL_SEC` | `3600` | Wall-clock TTL |
| `MATURING_WATCHLIST_MAX_ENTRIES` | `40` | Cap (evict oldest last_seen) |
| `MULTI_DURATION_PARALLEL` | `True` | gather place_order after one sync (same entry time) |
| `MULTI_DURATION_IGNORE_SESSION_BLOCKS` | `True` | data mode: multi batch ignores Massaniello session complete/exhausted |
| `DURATION_SEC` | `900` | Vencimiento 15 min (revertido a 900s 2026-07-20) |
| `DAILY_LOSS_GUARD_ENABLED` | `False` | Modo 24h: sin freno por pérdida diaria (lee módulo config, no `_runner._config`) |

---

## Feature list snapshot

| ID | Name | Status |
|----|------|--------|
| 1–7 | STRAT-F + hub | done |
| 8 | schedule_auto | in_progress (paused) |
| 9 | stoch_entry_help | **done** |
| 10 | smart_order_place | **done** |
| 11 | maturing_zone_watchlist | **done** (2026-07-17, reviewer APPROVE) |
| 15 | parallel_scan_fase3 | **done** (2026-07-17, auditado+corregido) |
| 16 | strat_f_maturing_m15_recheck | **done** (2026-07-19) |
| 17 | watchdog_bot | **done** (2026-07-19) — `scripts/watchdog_bot.py` cron cada 5 min |

Ad-hoc (documented in changelog, no feature id): Massaniello 24/7, scan 5m, countdown log, quiet trade wait, vencimiento 10min + DAILY_LOSS_GUARD_ENABLED=False.

---

## Known problems

| ID | Problem | Severity |
|----|---------|----------|
| P1 | ~~Tests fail if bankroll sets min_payout=90~~ | **fixed** — `QUOTEX_TEST_MODE` / skip hydrate under pytest |
| P2 | M1 micro-trend pre-buy gate not implemented | low (design only) — may already be in progress |
| P3 | schedule_auto / duration_live formal close | low |
| P4 | ~~Log file can grow large~~ | **fixed** — RotatingFileHandler 2MB×3 |
| P5 | ~~Console X / Ctrl+C leave orphans / hang~~ | **fixed** — foreground bat + hard-timeout cleanup + PID lock |

---

## Next focus

1. Run 24/7 PRACTICE; fill black box with math filters + contextual scoring + stoch zone/action + outcomes.
2. Optional SDD: M1 micro-trend confirm before buy.
3. Housekeeping: schedule_auto review.
