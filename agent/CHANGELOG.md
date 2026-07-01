# CHANGELOG — Project Evolution

> Human-readable chronological history. Newest entries at the top.
> Technical session detail: `progress/history.md` (Harness) and `agent/HANDOFF.md`.

---

## 2026-06-30

### Added
- **Features #4, #5, #6** — `candle_cache.py`, `entry_sync.py`, `strat_momentum.py`; 13 new tests (74 total).
- **Feature #3 `parallel_asset_scan`** — `parallel_fetch.py`; prefetch paralelo 5m+1m en `scanner.py`; 3 new tests (61 total).
- **Feature #2 `implement_missing_modules`** — `smc_analysis.py`, `smc_decision_engine.py`, `smc_auto_trader.py`, `filter_and_sell_otc.py`; 18 new tests (58 total).

### Completed features
- **#4 `candle_cache`** — Caché incremental por activo/tf; reviewer APPROVED.
- **#5 `entry_sync_precision`** — Sincronización open 1m, lag ≤ 0.3s; reviewer APPROVED.
- **#6 `strategy_momentum_1m`** — STRAT-MOMENTUM en scanner; reviewer APPROVED.
- **#3 `parallel_asset_scan`** — Escaneo paralelo OTC; reviewer APPROVED.
- **#2 `implement_missing_modules`** — SMC stack + filter-sell OTC; reviewer APPROVED.

### Changed
- **`feature_list.json`** — #4, #5, #6 → `done`; progress 7/16; next `#7 strategy_reversal_swing`.
- **`agent/PROJECT_STATE.md`, `agent/TASKS.md`, `agent/HANDOFF.md`** — synced for #4–#6 closure.
- **`docs/ROADMAP.md`** — Fase 1 completa; Fase 2 en curso (momentum done).

---

## 2026-06-29

### Added
- **`/agent` autonomous workflow** — `START.md`, `SESSION_PROTOCOL.md`, `PROJECT_STATE.md`, `TASKS.md`, `DECISIONS.md`, `CHANGELOG.md`, `CONTEXT.md`, `HANDOFF.md`.
- **`docs/ROADMAP.md`** — phased roadmap with dependencies, module inventory, changelog.
- **Feature #16 `massaniello_risk`** — `massaniello_engine.py`, `massaniello_risk.py`; 13 new tests.
- **SDD harness** — `AGENTS.md`, `init.ps1`, `feature_list.json`, `specs/`, `.claude/agents/`.

### Changed
- **`feature_list.json`** — 16 features with phases, `depends_on`, blockers; #11 → `massaniello_persistence`.
- **`docs/architecture.md`** — Massaniello in data flow; martingale deprecated.
- **`CHECKPOINTS.md`** — evaluated against current state.
- **`MARTINGALE_SUMMARY.md`** — marked LEGACY.

### Completed features
- **#1 `refactor_monolith`** — monolith → 8 modules; facade 292 lines; 27 tests.
- **#16 `massaniello_risk`** — martingale replaced; demo PRACTICE enforced; 40 tests total.

### Fixed
- R14 CLI test coverage (`test_parse_args_legacy_cli_flags`) during #1 review.

### Known issues
- Quotex demo login rejected (invalid credentials in `.env`).
- Massaniello live validation (5 entries / 3 wins / 1h) not yet executed.

---

## 2026-06-29 (earlier)

### Added
- Initial project harness creation (15 features, all `pending`).
- `progress/current.md`, `progress/history.md` lifecycle files.

---

## Pre-changelog (legacy state)

### Existing systems (before SDD harness)
- `consolidation_bot.py` monolith (~4000 lines).
- Strategies: consolidation (A), Wyckoff spring/sweep (B).
- `entry_scorer.py`, `trade_journal.py`, `martingale_calculator.py`.
- `README.md` with basic setup instructions.