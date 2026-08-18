# Repo audit — 2026-08

## Objective

Reduce repository entropy without changing trading behaviour. Structural refactors must preserve imports through temporary compatibility shims until consumers are migrated.

## Canonical domains established

- `src/data/` — market-data acquisition and caching (`candle_cache`, `parallel_fetch`, `scan_prefetch`).
- `src/decision/` — entry scoring and entry policy (`entry_scorer`, `entry_decision_engine`).
- `src/risk/` — Massaniello sizing/session risk (`massaniello_engine`, `massaniello_risk`).
- `src/strategies/` — strategy-specific implementations. SMC and STRAT-A Radar have been migrated here; additional strategies are being classified before migration.
- `src/lab/` / `src/strategy_lab/` — research/backtesting/experimentation; do not mix with production orchestration.

## Files intentionally not deleted yet

- `src/scanner.py`: still a production orchestrator with multiple responsibilities. It must be decomposed by dependency boundary, not moved wholesale.
- `src/consolidation_bot.py`: coordinates scanner/execution/risk and therefore requires dependency mapping before extraction.
- `src/executor.py`: contains execution plus lifecycle/session behaviour; split only after callers and side effects are mapped.
- Strategy modules whose production usage is not yet proven (`strat_a.py`, `strat_fractal.py`, stochastic helpers, etc.).

## Confirmed cleanup

- Removed `.pocket_profile/` local browser/runtime state.
- Removed `.atl/.skill-registry.cache.json` generated cache.
- Removed `.vscode/settings.json` local editor settings.
- Removed generated `graphify-out/` artifacts and ignored the directory.
- Removed obsolete `scanner_spec_only.patch`; it was a standalone patch artifact, not executable project code.

## Migration rule

1. Classify a module by responsibility.
2. Prove consumers and imports.
3. Move/extract with a compatibility shim when practical.
4. Verify imports/tests.
5. Remove the shim only after the old path is unused.
6. Never change trading thresholds, strategy gates, risk parameters, or execution semantics as part of structural cleanup.

## Next extraction order

1. Finish strategy dependency inventory.
2. Extract only strategy modules with clear production boundaries.
3. Separate scanner data/decision/strategy side effects.
4. Separate execution from lifecycle/session policy.
5. Reduce `scanner.py` and `consolidation_bot.py` to orchestration.
6. Run import/test verification and remove obsolete shims.
