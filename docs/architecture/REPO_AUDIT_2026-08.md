# Repo audit — 2026-08

## Objective

Reduce repository entropy without changing trading behaviour. Structural refactors must preserve imports through temporary compatibility shims until consumers are migrated.

## Canonical domains established

- `src/core/` — shared domain models and domain defaults.
- `src/data/` — market-data acquisition and caching (`candle_cache`, `parallel_fetch`, `scan_prefetch`).
- `src/decision/` — entry scoring and entry policy (`entry_scorer`, `entry_decision_engine`).
- `src/risk/` — Massaniello sizing/session risk (`massaniello_engine`, `massaniello_risk`).
- `src/indicators/` — shared market-analysis entry points; stochastic is currently exposed here without duplicating its implementation.
- `src/strategies/` — strategy-specific implementations and transitional compatibility surfaces. SMC, STRAT-A Radar, Momentum, Reversal Swing and Order Block now have canonical strategy namespaces.
- `src/execution/` — execution contracts; `executor.py` remains the production implementation until its lifecycle responsibilities are split safely.
- `src/lab/` / `src/strategy_lab/` — research/backtesting/experimentation; do not mix with production orchestration.

## Confirmed cleanup

- Removed generated `.pocket_profile/` runtime state.
- Removed generated `.atl/.skill-registry.cache.json` cache.
- Removed local `.vscode/settings.json`.
- Removed generated `graphify-out/` artifacts and ignored the directory.
- Removed obsolete `scanner_spec_only.patch` standalone patch artifact.
- Hardened `.gitignore` for pytest, coverage, mypy and ruff generated state.

## Compatibility policy

Root strategy modules that have active consumers remain as small shims until their references are migrated. A shim is not considered dead code merely because a canonical implementation exists.

## Intentionally not deleted yet

- `src/models.py`: still has production/research consumers; migration to `core.models` must finish first.
- `src/config.py`: contains runtime/hot-reload state and must be split without changing values.
- `src/scanner.py`: production orchestrator with multiple responsibilities; decompose by dependency boundary.
- `src/consolidation_bot.py`: coordinates scanner/execution/risk and needs dependency mapping.
- `src/executor.py`: execution plus lifecycle/session behaviour; split only after side effects are mapped.
- Strategy modules whose production/legacy status is not yet proven.

## Migration rule

1. Classify a module by responsibility.
2. Prove consumers and imports.
3. Move/extract with a compatibility shim when practical.
4. Verify imports/tests.
5. Remove the shim only after the old path is unused.
6. Never change trading thresholds, strategy gates, risk parameters, or execution semantics as part of structural cleanup.
