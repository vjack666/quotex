# Explore: Split `consolidation_bot.py` into modules

**Date:** 2026-06-29  
**Source:** `src/consolidation_bot.py` (**4,171 lines** — larger than the ~3,800 estimate)  
**Goal modules:** `connection.py`, `scanner.py`, `executor.py`, `strat_a.py`, `strat_b.py`

---

## 1. File map (high level)

| Lines | Section |
|------:|---------|
| 1–34 | Module docstring |
| 35–101 | Imports, `.env` bootstrap, logging setup |
| 103–238 | Strategy / runtime constants (100+ module-level knobs) |
| 241–320 | Dataclasses: `TradeState`, `EntryTimingInfo`, `PendingReversal`, `MartinPending`, `OrderBlock`, `MAState` |
| 244 | `from models import Candle, ConsolidationZone` |
| 323–485 | Pure analysis helpers (candle parse, ATR, consolidation, zone touch/break) |
| 488–879 | Broker helpers: `fetch_candles*`, `get_open_assets`, `looks_like_connection_issue`, `place_order` |
| 882–3921 | `class ConsolidationBot` (~3,040 lines) |
| 3924–4171 | `main()` loop, CLI (`parse_args`), `if __name__` |

### `ConsolidationBot` method index (by concern)

| Lines | Method | Concern |
|------:|--------|---------|
| 887–959 | `__init__` | Orchestrator state |
| 961–1081 | Broken-zone forensic capture | STRAT-A audit / background tasks |
| 1083–1165 | Balance, amounts, payout, price | Risk + executor support |
| 1167–1259 | Threshold, blacklist, asset limits | STRAT-A filters |
| 1261–1617 | Order blocks, MA, dry-run summaries | STRAT-A scoring |
| 1645–1695 | Martin limits, background task mgmt | Executor / risk |
| 1697–1920 | Martin enter, monitor, pending martin | Executor |
| 1922–2024 | Rejection candle, cycle reset/update | STRAT-A + risk |
| 2026–2166 | `refresh_balance_and_risk`, `reconcile_pending_candidates` | Risk + journal |
| 2168–2291 | `_strategy_snapshot`, `_sync_to_next_candle_open` | Journal + executor timing |
| 2293–2459 | `_process_pending_reversals` | STRAT-A |
| **2461–3495** | **`scan_all`** | **Scanner + STRAT-A + STRAT-B orchestration** |
| 3497–3542 | `ensure_connection` | Connection |
| 3545–3722 | `_resolve_trade` | Executor |
| 3724–3883 | `_check_martin`, `_enter` | Executor |
| 3885–3921 | `log_stats` | Orchestrator |

---

## 2. Existing partial modules in `src/`

| File | Role | Overlap with monolith |
|------|------|------------------------|
| `models.py` | `Candle`, `ConsolidationZone` | Already extracted (line 244 imports from here) |
| `entry_scorer.py` | `CandidateEntry`, `score_candidate`, `select_best`, `explain_score` | STRAT-A scoring; imports `models` to avoid circular imports |
| `candle_patterns.py` | `detect_reversal_pattern`, `explain_no_pattern_reason` | STRAT-A 1m reversal confirmation |
| `strategy_spring_sweep.py` | `detect_spring_or_upthrust` (+ spring/upthrust/wyckoff_early) | **Core STRAT-B detector** — already isolated |
| `martingale_calculator.py` | `MartingaleCalculator` | Position sizing / gale math |
| `trade_journal.py` | `get_journal()` SQLite black box | Used by scanner decisions + executor outcomes |

**Not present yet:** `connection.py`, `scanner.py`, `executor.py`, `strat_a.py`, `strat_b.py`, `config.py`

**Related outside `src/`:** `main.py` (repo root) — thin CLI wrapper over `consolidation_bot.main()`; `src/__pycache__/main.cpython-313.pyc` suggests an older `src/main.py` may have existed.

---

## 3. Strategy A vs Strategy B mapping

### STRAT-A — Consolidation / rebound / breakout (primary)

**Identity in code:** `strategy_origin="STRAT-A"` (default on `TradeState`, line 261)

**Business logic (docstring lines 6–16):**
1. Scan OTC assets with payout ≥ 80%
2. Detect 5m consolidation (min 12–15 bars, tight range)
3. **Rebound:** PUT at ceiling, CALL at floor
4. **Breakout:** strong break + high volume → immediate entry (optional martingale on 2nd minute — mostly deferred martin path now)
5. Score with `entry_scorer` + adaptive threshold; operate best candidate only

**Entry modes (`entry_mode`):**
- `rebound_ceiling` → PUT
- `rebound_floor` → CALL
- `breakout_above` → CALL (BROKEN_ABOVE)
- `breakout_below` → PUT (BROKEN_BELOW)

**Key code regions:**
- `scan_all` STRAT-A branch: **2725–3210** (after STRAT-B block per asset)
- Candidate build + filters: **2845–3209**
- Selection + execution: **3311–3490** (`select_best`, `_enter(..., strategy_origin="STRAT-A")`)
- `_process_pending_reversals`: **2293–2459**
- `_validate_rejection_candle`: **1922–1969**
- OB/MA scoring: **1261–1617**, applied in scan at **3176–3207**
- Uses: `detect_consolidation`, `price_at_*`, `broke_*`, `is_high_volume_break`, `infer_h1_trend`, `candle_patterns`, `entry_scorer`

**Stats keys:** `strat_a_signals`, `strat_a_wins`, `strat_a_losses`

---

### STRAT-B — Spring Sweep / Wyckoff (parallel, optional live)

**Identity in code:** `strategy_origin="STRAT-B"`; constants **225–232**

**Detector:** `strategy_spring_sweep.detect_spring_or_upthrust()` — **not** inline in monolith

**Signal types:** `spring`, `upthrust`, `wyckoff_early_spring`, `wyckoff_early_upthrust`

**Behavior:**
- Runs **per asset inside `scan_all`** on 1m candles (sequential fetch to avoid WS cross-talk)
- Default: **mirror/log mode** (`STRAT_B_CAN_TRADE = False` unless `--strat-b-live` via root `main.py`)
- When live: enters immediately if `confidence >= STRAT_B_MIN_CONFIDENCE` (or early wyckoff threshold), **bypasses** STRAT-A score threshold
- Duration: `STRAT_B_DURATION_SEC` (30 default in monolith; root `main.py` overrides to 120)

**Key code regions:**
- Per-asset evaluation: **2598–2723**
- Cycle summary logging: **3218–3273**
- Post-trade stats: **3624–3634**, **3866–3867**
- Support diagnostic: `find_strong_support_2m` **554–608** (used in STRAT-B summary only)

**Stats keys:** `strat_b_signals`, `strat_b_wins`, `strat_b_losses`

---

## 4. Proposed module: `connection.py`

**Responsibility:** Quotex session lifecycle, candle/instrument fetch, connection error classification.

### Move as-is (standalone functions)

| Symbol | Lines | Notes |
|--------|------:|-------|
| `fetch_candles` | 491–508 | Wraps `client.get_candles` → `List[Candle]` |
| `fetch_candles_with_retry` | 511–551 | Timeout + backoff |
| `get_open_assets` | 611–631 | OTC open + payout filter |
| `looks_like_connection_issue` | 634–641 | Shared by connection + `place_order` + main loop |
| `connect_with_retry` | 3976–3995 | Initial connect + Cloudflare 403 backoff |
| `raw_to_candle` | 326–336 | Could live here or `models`/scanner |

### Move from `ConsolidationBot` / `place_order`

| Symbol | Lines | Notes |
|--------|------:|-------|
| `ensure_connection` | 3497–3542 | Health-check reconnect in 24/7 loop |
| `_force_reconnect` (nested in `place_order`) | 665–711 | **Extract** to `async def force_reconnect(client, ...)` |

### Constants to colocate

```
CONNECT_RETRIES, RECONNECT_TIMEOUT_SEC, HEALTHCHECK_RECONNECT_RETRIES,
CF_403_BACKOFF_SEC, FETCH_RETRIES, FETCH_RETRY_BACKOFF_SEC,
CANDLE_FETCH_TIMEOUT_SEC, CANDLE_FETCH_1M_TIMEOUT_SEC, H1_FETCH_TIMEOUT_SEC,
CANDLE_FETCH_CONCURRENCY, MIN_PAYOUT
```

### Dependencies

- **In:** `pyquotex.Quotex`, `models.Candle`, logging
- **Out:** Used by `scanner`, `executor`, `strat_*`, orchestrator

---

## 5. Proposed module: `scanner.py`

**Responsibility:** Asset scan loop infrastructure, consolidation/zone detection, technical context (OB, MA, ATR), **without** strategy-specific entry decisions.

### Pure analysis (move from top-level)

| Symbol | Lines |
|--------|------:|
| `avg_body`, `is_high_volume_break` | 339–355 |
| `_clamp`, `_ema`, `compute_atr`, `infer_h1_trend` | 358–406 |
| `detect_consolidation` | 409–461 |
| `price_at_ceiling`, `price_at_floor`, `broke_above`, `broke_below` | 464–485 |
| `find_strong_support_2m` | 554–608 |

### Move from `ConsolidationBot` (static / stateless preferred)

| Symbol | Lines | Notes |
|--------|------:|-------|
| `_detect_order_blocks` | 1262–~1400 | Returns `dict[str, list[OrderBlock]]` |
| `_score_order_blocks` | 1413–~1518 | STRAT-A adjunct — could stay in `strat_a` instead |
| `_compute_ma_state` | 1519–1555 | |
| `_score_ma` | 1556–1579 | |

### Orchestration to extract from `scan_all`

| Concern | Lines | Suggested API |
|---------|------:|---------------|
| Asset list + cap | 2470–2482 | `prepare_asset_universe(client)` |
| Parallel 5m prefetch | 2526–2561 | `AssetCandleFetcher` with semaphore |
| Sequential 1m fetch | 2539–2553 | Same class, `fetch_1m(symbol)` |
| Zone registry update | 2745–2781 | `update_zone_state(zones, sym, zone, ...)` |
| Price contamination guards | 2786–2812 | `validate_price(sym, price, zone, last_known)` |
| Greylist / blacklist / failed_assets skips | 2578–2594 | `should_skip_asset(bot_state, sym)` |

**Note:** `scan_all` (2461–3495, ~1,035 lines) should shrink to: fetch → call `strat_b.evaluate(...)` → call `strat_a.evaluate(...)` → merge candidates → hand off to executor.

### Dataclasses (candidates for `models.py` or `scanner.py`)

- `OrderBlock` (303–311)
- `MAState` (314–320)

### Dependencies

- **In:** `connection`, `models`, `config` constants
- **Out:** `strat_a`, `strat_b`, orchestrator

---

## 6. Proposed module: `executor.py`

**Responsibility:** Order placement, entry timing, trade lifecycle, martingale execution paths.

### Top-level functions

| Symbol | Lines | Notes |
|--------|------:|-------|
| `place_order` | 644–879 | Uses reconnect helpers → import from `connection` |

### `ConsolidationBot` methods to move (as `TradeExecutor` class or module functions)

| Symbol | Lines | Notes |
|--------|------:|-------|
| `_enter` | 3748–3883 | Central entry point for both strategies |
| `_sync_to_next_candle_open` | 2224–2291 | 1m candle sync / reject late |
| `_resolve_trade` | 3545–3722 | WIN/LOSS + journal + triggers martin |
| `_resolve_trade_after_expiry` | 1868–1872 | Background task wrapper |
| `_check_martin` | 3724–3743 | Expired trade cleanup |
| `_monitor_trade_live` | 1789–1866 | Anticipated martin while trade open |
| `_try_enter_martin_now` | 1708–1787 | Immediate/deferred martin |
| `_process_pending_martin` | 1874–1920 | Martin on next valid candidate |
| `_get_current_price` | 1145–1156 | Uses `fetch_candles_with_retry` |
| `_get_asset_payout` | 1135–1143 | Uses `get_open_assets` |

### Dataclasses

| Symbol | Lines |
|--------|------:|
| `TradeState` | 247–265 |
| `EntryTimingInfo` | 268–275 |
| `MartinPending` | 292–300 |

### Constants

```
DURATION_SEC, ENTRY_SYNC_TO_CANDLE, ENTRY_MAX_LAG_SEC, ENTRY_REJECT_LAST_SEC,
ORDER_SEND_RETRIES, MAX_CONCURRENT_TRADES, COOLDOWN_BETWEEN_ENTRIES,
MARTIN_* (all), MIN_ORDER_AMOUNT, TF_1M
```

### Dependencies

- **In:** `connection.place_order`, `connection.fetch_*`, `trade_journal`, `martingale_calculator`, `models`
- **Out:** Called by orchestrator + strat modules (STRAT-B calls `_enter` directly today at 2709)

---

## 7. Proposed module: `strat_a.py`

**Responsibility:** Consolidation rebound/breakout signal generation, pending reversals, scoring pipeline, candidate selection.

### Move from `ConsolidationBot`

| Symbol | Lines |
|--------|------:|
| `_validate_rejection_candle` | 1922–1969 |
| `_required_rebound_strength` | 1168–1169 |
| `_is_put_pattern_blacklisted` | 1172–1173 |
| `_process_pending_reversals` | 2293–2459 |
| `_update_dynamic_threshold` | 1175–1187 |
| `_record_scan_acceptances` | 1189–1190 |
| `_threshold_label`, `_threshold_change_reason` | 1580–1593 |
| `_log_dry_run_verbose_cycle_summary` | 1619–1643 |
| OB/MA scoring helpers | 1413–1579 | If not kept in scanner |

### Extract from `scan_all` (STRAT-A body)

| Block | Lines | Purpose |
|-------|------:|---------|
| Dynamic ATR range | 2729–2743 | Per-asset range tolerance |
| Zone + direction detection | 2745–2930 | Rebound vs breakout |
| Zone age gate | 2932–2945 | `ZONE_AGE_*` |
| 1m pattern + rejection flow | 2947–3083 | `candle_patterns`, `PendingReversal` |
| H1 trend filter | 3085–3106 | `infer_h1_trend` |
| Candidate scoring | 3108–3209 | `score_candidate` + bonuses |
| Post-scan selection | 3311–3490 | `select_best`, journal, `_enter` STRAT-A |

### Dataclass

- `PendingReversal` (278–289)

### Suggested public API

```python
async def evaluate_asset(ctx, sym, payout, candles_5m, candles_1m, ...) -> Optional[CandidateEntry]
async def process_pending_reversals(ctx, ...) -> list[CandidateEntry]
def select_and_rank(candidates, threshold) -> tuple[list, list]
```

### Dependencies

- **In:** `scanner` (zone math), `entry_scorer`, `candle_patterns`, `models`, `config`
- **Out:** Returns `CandidateEntry` list to orchestrator / executor

---

## 8. Proposed module: `strat_b.py`

**Responsibility:** Spring Sweep evaluation, confidence gating, optional autonomous entry.

### Already external

- `strategy_spring_sweep.detect_spring_or_upthrust` — keep as low-level detector; `strat_b.py` wraps it

### Extract from `scan_all`

| Block | Lines |
|-------|------:|
| 1m DataFrame build + detect | 2612–2628 |
| Confidence gating + live entry | 2630–2723 |
| Cycle summary + support log | 3218–3273 |

### Suggested public API

```python
@dataclass
class StratBSignal:
    asset: str
    payout: int
    direction: str
    confidence: float
    signal_type: str
    reason: str
    candles_1m: list[Candle]

def evaluate(candles_1m: list[Candle], *, allow_early: bool) -> StratBSignal | None
async def maybe_enter(signal, executor, *, can_trade: bool) -> bool
async def log_cycle_summary(hits, nearmiss, client) -> None
```

### Constants

```
STRAT_B_CAN_TRADE, STRAT_B_DURATION_SEC, STRAT_B_MIN_CONFIDENCE,
STRAT_B_MIN_CONFIDENCE_EARLY, STRAT_B_ALLOW_WYCKOFF_EARLY,
STRAT_B_LOG_TOP_N, STRAT_B_PREVIEW_MIN_CONF
```

### Dependencies

- **In:** `strategy_spring_sweep`, `scanner.find_strong_support_2m`, `connection` (2m candles for log), `executor._enter`, `entry_scorer.CandidateEntry` (journal shim), `trade_journal`

---

## 9. What stays in `consolidation_bot.py` vs `main.py`

### `consolidation_bot.py` (or rename → `bot.py` / keep as facade)

| Keep | Lines | Reason |
|------|------:|--------|
| `ConsolidationBot` shell | 885–959 | Owns mutable session state (`zones`, `trades`, `stats`, blacklists) |
| `scan_all` thin orchestrator | 2461+ | Delegates to strat/scanner/executor |
| Risk / session | 1083–1112, 2026–2054, 1971–2024 | Balance, drawdown stop, Masaniello cycle |
| Asset blacklist / limits | 1192–1259, 1214–1233 | Cross-strategy |
| Broken-zone forensic capture | 961–1081 | Operational audit (STRAT-A breakout) |
| `reconcile_pending_candidates` | 2056–2166 | Startup / periodic journal hygiene |
| `_strategy_snapshot` | 2168–2222 | Journal metadata |
| `log_stats` | 3885–3921 | |
| `shutdown_background_tasks` | 1686–1695 | |
| Logging + `.env` bootstrap | 54–101 | Or move to `config.py` |
| Module constants | 103–238 | Or `config.py` |
| `async def main(...)` | 3998–4113 | Could move entirely to root `main.py` |
| `sleep_with_inline_countdown`, `seconds_until_next_scan` | 3927–3973 | Loop utilities |

### Root `main.py` (already exists)

- CLI parsing (`--real`, `--once`, `--hub-readonly`, `--strat-b-live`, cycle/martingale overrides)
- `_apply_runtime_config` patches `consolidation_bot` module globals
- HUB readonly loop
- **Target state:** import `ConsolidationBot` from package; patch `config` instead of monolith module

### `consolidation_bot.py` `if __name__` block (4148–4171)

Legacy CLI (`--live`, `--loop`, `--greylist`). Root `main.py` is the preferred entry; consider deprecating duplicate `parse_args`.

---

## 10. Import / dependency graph (current)

```
consolidation_bot.py
├── pyquotex.stable_api.Quotex
├── models (Candle, ConsolidationZone)
├── entry_scorer (CandidateEntry, score_candidate, select_best, explain_score)
├── candle_patterns (detect_reversal_pattern, explain_no_pattern_reason)
├── strategy_spring_sweep (detect_spring_or_upthrust)  ← STRAT-B core
├── trade_journal (get_journal)
├── martingale_calculator (MartingaleCalculator)
└── pandas (STRAT-B DataFrame bridge only)

entry_scorer.py → models
main.py → consolidation_bot (dynamic import)
```

### Target dependency graph (no cycles)

```
config.py          ← all constants + .env
models.py          ← Candle, ConsolidationZone, shared dataclasses

connection.py      → config, models, pyquotex
scanner.py         → connection, models, config
strat_a.py         → scanner, entry_scorer, candle_patterns, models, config
strat_b.py         → strategy_spring_sweep, scanner, models, config
executor.py        → connection, trade_journal, martingale_calculator, models, config
consolidation_bot.py → connection, scanner, strat_a, strat_b, executor, config
main.py            → consolidation_bot (or package __init__)
```

**Circular-import risk today:** `models` was split specifically because `entry_scorer` ↔ `consolidation_bot` cycled. Keep `CandidateEntry` in `entry_scorer`; strategies attach ephemeral attrs via `setattr` (pattern used throughout scan).

---

## 11. Coupling hotspots (hardest splits)

1. **`scan_all` (1,035 lines)** — interleaves STRAT-B inline entry, STRAT-A pipeline, pending reversals, martin, and final selection. Split order: extract STRAT-B block first (self-contained), then STRAT-A candidate builder, leave orchestration in bot.

2. **`place_order` reconnect logic** — duplicated pattern with `connect_with_retry` / `ensure_connection`. Unify in `connection.py` before moving executor.

3. **`_enter` ↔ journal ↔ timing ↔ stats** — single funnel for both strategies; executor should own this; strategies only produce intent objects.

4. **Module-level mutable constants** — `main.py` and CLI mutate `cb.SCAN_MAX_ASSETS_PER_CYCLE`, `STRAT_B_*`, etc. Introduce `config.py` or `BotConfig` dataclass passed into bot constructor.

5. **Martingale after LOSS in `_resolve_trade`** — ties executor to strat origin + zones; keep in executor but inject zone lookup callback.

---

## 12. Recommended extraction order

1. **`config.py`** — constants 103–238 + credentials (reduces churn in other files)
2. **`connection.py`** — fetch + connect + `looks_like_connection_issue`
3. **`executor.py`** — `place_order`, `TradeState`, `_enter`, resolve/monitor/martin
4. **`strat_b.py`** — smallest independent slice; already has `strategy_spring_sweep.py`
5. **`scanner.py`** — pure detection + fetch orchestration helpers
6. **`strat_a.py`** — largest logic block from `scan_all` + pending reversals
7. **Thin `consolidation_bot.py`** — state bag + `scan_all` orchestration + `main` loop
8. **Align root `main.py`** — sole CLI entry, import from package

---

## 13. Line-count budget after split (estimate)

| Module | Approx. lines |
|--------|-------------|
| `config.py` | ~150 |
| `connection.py` | ~350 |
| `scanner.py` | ~550 |
| `executor.py` | ~900 |
| `strat_a.py` | ~1,100 |
| `strat_b.py` | ~250 |
| `consolidation_bot.py` (residual) | ~700 |
| **Total** | ~4,000 (same logic, less duplication) |

---

## 14. Quick reference: symbols → target module

| Symbol | Target |
|--------|--------|
| `connect_with_retry`, `ensure_connection`, `fetch_candles*`, `get_open_assets` | `connection.py` |
| `detect_consolidation`, `compute_atr`, `infer_h1_trend`, OB/MA detect | `scanner.py` |
| `place_order`, `_enter`, `_resolve_trade*`, martin monitor/enter | `executor.py` |
| Rebound/breakout, pending reversals, `select_best` pipeline | `strat_a.py` |
| `detect_spring_or_upthrust` wrapper + STRAT_B_* gating | `strat_b.py` |
| `ConsolidationBot`, `scan_all` orchestration, `main` loop, risk cycle | `consolidation_bot.py` / `main.py` |
| `Candle`, `ConsolidationZone` | `models.py` (done) |
| `detect_spring_or_upthrust` implementation | `strategy_spring_sweep.py` (done) |