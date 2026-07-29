# Tasks — multi_tf_correlation

> **Feature ID:** 19
> **Estimated effort:** 3-5 days
> **Order:** Execute sequentially

---

- [ ] T1 — Create `src/multi_tf_correlation.py` with `detect_trend()`, `calculate_confluence()`, `compute_confluence_bonus()`. Cubre: R1, R2, R3, R6.
- [ ] T2 — Add CONFLUENCE_* constants to `src/config.py`. Cubre: R7.
- [ ] T3 — Create `tests/test_multi_tf_correlation.py` with 12+ tests: 4/4 aligned, 3/4, 2/4, H1 unavailable, neutral TF, threshold, mock candles. Cubre: R8.
- [ ] T4 — Integrate confluence in `src/scanner.py` after STRAT-F evaluation: compute bonus, adjust score, add logging. Cubre: R4, R5.
- [ ] T5 — Add integration test in `tests/test_multi_tf_correlation.py` verifying scanner applies confluence bonus correctly with mock candles. Cubre: R4, R8.
- [ ] T6 — Run full test suite, verify no regressions. Cubre: R8.
- [ ] T7 — Commit, push, update `feature_list.json` status to done.
