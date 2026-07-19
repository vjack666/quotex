# PROJECT_STATE

> Last updated: 2026-07-17 (changelog session: stoch, order, 24/7, 5m align, quiet logs)
> Full detail: `docs/CHANGELOG_2026-07-16.md`

---

## Project identity

| Field | Value |
|-------|-------|
| Name | quotex-hft-bot |
| Type | HFT binary options bot for Quotex |
| Language | Python 3.10+ (running 3.13/3.14) |
| Risk manager | **Massaniello** (ops / ITM / timeout / PRACTICE) |
| Strategy focus | **STRAT-F** live + **stoch M15 help hard** |
| Roadmap | #1–#7 done; #9–#10 done; #11 maturing_zone_watchlist impl complete (await review); #8 schedule_auto paused |
| Data collection | **24/7** — cycle end resets Massaniello only |

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
  → compute_stoch + apply_stoch_help (hard)
  → mature re-eval: live→candidate / shadow→metrics only
  → candidate → Massaniello → enter_trade (prewarm + 1m sync)
  → if open trade: quiet wait (no scan)
  → resolve → next cycle
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

---

## Feature list snapshot

| ID | Name | Status |
|----|------|--------|
| 1–7 | STRAT-F + hub | done |
| 8 | schedule_auto | in_progress (paused) |
| 9 | stoch_entry_help | **done** |
| 10 | smart_order_place | **done** |
| 11 | maturing_zone_watchlist | **done** (2026-07-17, reviewer APPROVE) |

Ad-hoc (documented in changelog, no feature id): Massaniello 24/7, scan 5m, countdown log, quiet trade wait.

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

1. Run 24/7 PRACTICE; fill black box with stoch zone/action + outcomes.
2. Optional SDD: M1 micro-trend confirm before buy.
3. Housekeeping: schedule_auto review.
