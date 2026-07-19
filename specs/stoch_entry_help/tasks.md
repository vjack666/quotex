# Tasks — stoch_entry_help

> One feature only. Do not edit `src/strat_fractal.py`. TDD where practical:
> zones module first, then config, then scanner + black box, then integration.

- [x] T1 — Create `src/stochastic_zones.py` with `zone_from_k`, `StochHelpResult`, and `apply_stoch_help` (pure; bounds R2; matrix R3/R4; modes off/soft/hard; k=None; unknown mode fail-safe off). Cubre: R1, R2, R3, R4, R5, R6, R7, R9, R10, R16.

- [x] T2 — Add `tests/test_stochastic_zones.py`: boundary table (incl. 20→Z1, 80→Z5, clamp), full CALL/PUT × soft/hard matrix, mode off, k=None, case-insensitive direction, unknown mode. Cubre: R1, R2, R3, R4, R5, R6, R7, R9, R10, R17.

- [x] T3 — Add `STOCH_HELP_MODE` to `src/config.py` (`off`|`soft`|`hard`, default `"hard"`, env override). Cubre: R11, R16.

- [x] T4 — Wire `scanner.py` STRAT-F block: after `evaluate_strat_f` + `compute_stoch`, call `apply_stoch_help`; on VETO skip candidate with reject reason `stoch_extreme_against`; on BOOST add `score_delta` after `score_candidate`; leave `strat_fractal.py` untouched. Cubre: R8, R12, R13, R14, R5, R6, R7.

- [x] T5 — Enrich black box / `_rec` `stoch_m15` with `zone`, `action`, `score_delta` (including mode `off` measurement path). Cubre: R15.

- [x] T6 — Add `tests/test_stoch_entry_help_scanner.py` (mocked STRAT-F + stoch): hard CALL Z5 / PUT Z1 veto; soft no veto; boost raises score; mode off no effect; payload contains help fields. Cubre: R6, R7, R8, R13, R14, R15, R17.

- [x] T7 — Run new tests + full suite (`pytest` / `.\init.ps1`); fix regressions without changing STRAT-F core. Cubre: R12, R17.

- [x] T8 — Document traceability in `progress/impl_stoch_entry_help.md` (R → test map) for reviewer. Cubre: R17.
