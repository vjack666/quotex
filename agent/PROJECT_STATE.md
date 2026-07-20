# PROJECT_STATE

> Last updated: 2026-07-20 (math filters + contextual scoring)
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
| Roadmap | #1–#7 done; #9–#10 done; #11 done; #15 done; #16 done; #17 watchdog_bot done; #8 schedule_auto paused |
| Data collection | **24/7** — cycle end resets Massaniello only; `DAILY_LOSS_GUARD_ENABLED=False` en disco (sin freno diario) |

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
