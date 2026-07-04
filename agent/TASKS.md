# TASKS

> Maintained by agents at session end. Sync with `feature_list.json` and `docs/ROADMAP.md`.
> Last updated: 2026-07-04 — **Roadmap completo: 22/22 features done**

---

## In Progress

_None._

---

## Next

**Roadmap terminado.** Ninguna feature pendiente.

| Priority | Task | Notes |
|----------|------|-------|
| P1 | Validación live del sistema completo en PRACTICE | Probar todas las estrategias integradas |
| P2 | Rotar `consolidation_bot.log` periódicamente | ~63 MB al rotar |
| P3 | `parallel_fetch` DRY para OB prefetch (opcional) | Refactor menor |

---

## Completed

| ID | Task | Completed | Notes |
|----|------|-----------|-------|
| #1 | `refactor_monolith` | 2026-06-29 | Monolith → modular; 27 tests |
| #2 | `implement_missing_modules` | 2026-06-30 | SMC + filter_sell; 58 tests total |
| #3 | `parallel_asset_scan` | 2026-06-30 | Prefetch 5m+1m paralelo; 61 tests total |
| #4 | `candle_cache` | 2026-06-30 | Caché incremental; 74 tests total |
| #5 | `entry_sync_precision` | 2026-06-30 | EntrySynchronizer; lag ≤ 0.3s |
| #6 | `strategy_momentum_1m` | 2026-06-30 | STRAT-MOMENTUM en scanner |
| #7 | `strategy_reversal_swing` | 2026-07-04 | `strat_reversal_swing.py` |
| #8 | `strategy_order_block` | 2026-07-04 | `strat_order_block.py` |
| #9 | `backtesting_engine` | 2026-07-04 | `backtester.py` — 20 tests |
| #10 | `dynamic_weight_calibration` | 2026-07-04 | `weight_calibrator.py` — 36 tests |
| #11 | `massaniello_persistence` | 2026-07-04 | `massaniello_persistence.py` — 13 tests |
| #12 | `hub_live_websocket` | 2026-07-04 | Speadsheets desde docs/specs-temp/ |
| #13 | `kelly_criterion_sizing` | 2026-07-04 | `kelly_sizer.py` — 13 tests |
| #14 | `diversification_enforcer` | 2026-07-04 | `diversification_enforcer.py` — 13 tests |
| #15 | `telegram_alerts` | 2026-07-04 | `alerter.py` — 11 tests |
| #16 | `massaniello_risk` | 2026-06-29 | Replaces martingale; 40 tests at close |
| #17 | `strat_a_evaluate` | 2026-07-02 | `evaluate_strat_a()` en strat_a.py |
| #18 | `strat_a_test_suite` | 2026-07-02 | 16 unit + 9 E2E/pending; 109 tests total |
| #19 | `strat_a_quality_filters` | 2026-07-02 | Reject-first payout/score/zona |
| #20 | `strat_a_htf_zone_wiring` | 2026-07-02 | HTFScanner + zone_memory |
| #21 | `strat_a_ob_prefetch` | 2026-07-02 | OB prefetch paralelo |
| #22 | `strat_a_live_validation` | 2026-07-02 | Demo PRACTICE; 10 rechazos logged |

---

## Task movement rules

1. Move to **In Progress** when `feature_list.json` status → `in_progress`.
2. Move to **Completed** when reviewer approves and status → `done`.
3. Never have more than one feature In Progress (Harness rule).
4. Operational tasks (credentials, validation) stay in **Next** until resolved.
