# TASKS

> Maintained by agents at session end. Sync with `feature_list.json` and `docs/ROADMAP.md`.
> Last updated: 2026-06-30

---

## In Progress

_None._

---

## Next

Priority order — pick **one** feature per session (Harness rule).

| Priority | ID | Task | Phase | Depends on |
|----------|----|------|-------|------------|
| 1 | #7 | `strategy_reversal_swing` — reversión S/R dinámica | strategies | #5 ✅ |
| 2 | — | Fix Quotex demo credentials in `.env` | ops | human |
| 3 | — | Validate Massaniello live: 5 entries / 3 wins / 1h | validation | credentials |
| 4 | #8 | `strategy_order_block` — order blocks institucionales | strategies | #5 ✅ |

### Backlog (after strategies phase)

| ID | Task | Phase |
|----|------|-------|
| #9 | `backtesting_engine` | intelligence |
| #10 | `dynamic_weight_calibration` | intelligence |
| #11 | `massaniello_persistence` | operations |
| #12 | `hub_live_websocket` | operations |
| #13 | `kelly_criterion_sizing` | operations |
| #14 | `diversification_enforcer` | operations |
| #15 | `telegram_alerts` | operations |

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
| #16 | `massaniello_risk` | 2026-06-29 | Replaces martingale; 40 tests at close |
| — | Roadmap + docs sync | 2026-06-29 | `docs/ROADMAP.md`, feature_list.json updated |
| — | Agent workflow (`/agent`) | 2026-06-29 | Autonomous startup system created |

---

## Task movement rules

1. Move to **In Progress** when `feature_list.json` status → `in_progress`.
2. Move to **Completed** when reviewer approves and status → `done`.
3. Never have more than one feature In Progress (Harness rule).
4. Operational tasks (credentials, validation) stay in **Next** until resolved.