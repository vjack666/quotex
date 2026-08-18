# Quotex — Master Repository Restructure Checklist

Status: IN PROGRESS

## 0. Guardrails
- [x] Preserve trading behavior during structural refactor
- [x] Use compatibility shims while consumers migrate
- [x] Do not delete a module until references are audited
- [ ] Run import/test validation after each major migration batch
- [ ] Final full test/import validation

## 1. Repository hygiene
- [x] Ignore generated Graphify output
- [x] Remove generated `graphify-out/` from the current tree
- [x] Remove obsolete `scanner_spec_only.patch`
- [ ] Audit remaining generated/cache artifacts
- [ ] Audit large binaries/data accidentally tracked
- [ ] Confirm `.gitignore` covers generated runtime artifacts

## 2. Canonical domains
- [x] `src/data/` established
- [x] `src/decision/` established
- [x] `src/risk/` established
- [x] `src/strategies/` established
- [x] `src/core/` established
- [ ] `src/indicators/` established where shared analysis belongs
- [x] `src/execution/` established
- [ ] `src/analytics/` established if justified
- [ ] `src/lab/` boundaries documented and cleaned

## 3. Data layer
- [x] Migrate/expose `candle_cache`
- [x] Migrate/expose `parallel_fetch`
- [x] Migrate/expose `scan_prefetch`
- [ ] Audit connection/client modules
- [ ] Consolidate candle acquisition paths
- [ ] Remove obsolete data-layer shims after consumer migration

## 4. Decision layer
- [x] Migrate/expose `entry_decision_engine`
- [x] Migrate/expose `entry_scorer`
- [ ] Migrate all consumers to `decision.*`
- [ ] Remove old decision-module shims
- [ ] Verify no duplicated thresholds/policies

## 5. Risk layer
- [x] Migrate/expose `massaniello_engine`
- [x] Migrate/expose `massaniello_risk`
- [ ] Audit risk/session state modules
- [ ] Remove old risk-module shims after migration

## 6. Strategy layer
- [x] Establish SMC namespace
- [x] Establish STRAT-A namespace
- [x] Establish STRAT-F namespace
- [x] Expose candle-pattern utilities
- [x] Expose spike filter
- [x] Expose stochastic M15
- [x] Expose stochastic zones
- [x] Expose stochastic exhaustion
- [x] Expose stochastic early alert
- [x] Expose stochastic cross state
- [x] Move Momentum strategy implementation to `strategies/` with root shim
- [x] Move Reversal Swing strategy implementation to `strategies/` with root shim
- [x] Move Order Block strategy implementation to `strategies/` with root shim
- [ ] Audit all strategy implementations for active/legacy status
- [ ] Separate shared indicators from strategy-specific logic
- [ ] Migrate shared stochastic logic to `indicators/`
- [ ] Physically move STRAT-A implementation after dependency cleanup
- [ ] Physically move STRAT-F implementation after dependency cleanup
- [ ] Physically move remaining active strategies
- [ ] Remove obsolete strategy shims
- [ ] Remove dead strategy code only after reference/test audit

## 7. Core/domain models
- [x] Establish `core.models` compatibility namespace
- [x] Separate domain defaults from runtime config
- [x] Remove `models -> config` coupling where possible
- [ ] Migrate consumers to `core.models`
- [ ] Remove root `models.py` shim after migration

## 8. Configuration
- [ ] Inventory all config consumers
- [ ] Split operational config by responsibility
- [ ] Preserve all existing values during structural split
- [ ] Migrate consumers to canonical config namespaces
- [ ] Remove redundant config aliases

## 9. Scanner decomposition
- [ ] Map every scanner responsibility
- [x] Extract data/prefetch responsibilities
- [ ] Extract strategy dispatch
- [ ] Extract decision/scoring calls
- [ ] Extract journal/analytics side effects
- [ ] Extract execution calls
- [ ] Reduce scanner to orchestration
- [ ] Verify scanner behavior before deleting legacy paths

## 10. Consolidation bot
- [ ] Map responsibilities and dependencies
- [ ] Separate orchestration from policy
- [ ] Separate state/session handling
- [ ] Separate execution/risk integration
- [ ] Reduce `consolidation_bot.py` to orchestration
- [ ] Remove duplicated validation logic where proven equivalent

## 11. Execution
- [ ] Audit `executor.py`
- [ ] Separate broker/order execution
- [ ] Separate trade resolution
- [ ] Separate martingale/session logic from execution
- [x] Establish `src/execution/`
- [ ] Migrate consumers
- [ ] Remove execution shims/legacy modules

## 12. Lab / research
- [x] Keep `strategy_lab/` distinct from production paths
- [ ] Audit experiments and duplicate research utilities
- [ ] Move reusable production code out of lab
- [ ] Mark or remove obsolete experiments
- [ ] Ensure lab code cannot accidentally become a production dependency

## 13. Tests and verification
- [ ] Inventory test coverage by domain
- [ ] Add import smoke tests for canonical namespaces
- [ ] Add regression tests around scanner/consolidation behavior
- [ ] Verify risk calculations unchanged
- [ ] Verify strategy outputs unchanged
- [ ] Verify execution interfaces unchanged
- [ ] Run full test suite
- [ ] Run compile/import checks
- [ ] Check for unresolved old imports
- [ ] Check for circular imports

## 14. Final cleanup
- [ ] Remove all compatibility shims that are no longer needed
- [ ] Remove dead modules confirmed by reference audit
- [ ] Remove empty/obsolete directories
- [ ] Normalize naming conventions
- [ ] Update documentation and architecture diagrams
- [ ] Final repository tree audit
- [ ] Final Git diff/history sanity check
- [ ] Final CI/test verification

## Completion criterion

The restructure is COMPLETE only when every unchecked item above is either completed or explicitly documented as intentionally retained. The final report must include the final tree, removed modules, retained compatibility shims, validation results, and any intentionally deferred items.
