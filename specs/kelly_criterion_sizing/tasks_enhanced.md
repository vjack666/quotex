# Tasks — kelly_criterion_sizing (Enhanced)

> **Feature ID:** 20
> **Estimated effort:** 1 week
> **Depends on:** Feature 18 (LightGBM) must be done first
> **Order:** Execute sequentially

---

- [ ] T1 — Add KELLY_* constants to `src/config.py` (KELLY_ENABLED, KELLY_FRACTION, KELLY_MIN_TRADES, KELLY_ROLLING_WINDOW, KELLY_MIN_STAKE, KELLY_MAX_STAKE_PCT). Cubre: R4, R6.
- [ ] T2 — Enhance `src/kelly_sizer.py`: add `_rolling_win_rate()` using last N trades from DB. Cubre: R1.
- [ ] T3 — Add `_edge()` and `_dynamic_fraction()` methods to KellySizer. Cubre: R5.
- [ ] T4 — Add `_confidence_adjust()` method for ML integration. Cubre: R3.
- [ ] T5 — Update `calculate()` to return full dict with all details. Cubre: R1, R2, R3, R5.
- [ ] T6 — Add per-strategy filtering in `_rolling_win_rate()`. Cubre: R2.
- [ ] T7 — Add `_calculate_stake()` with min/max limits. Cubre: R6.
- [ ] T8 — Add `[KELLY]` logging in `calculate()`. Cubre: R7.
- [ ] T9 — Update `tests/test_kelly_sizer.py` with 10+ new tests: rolling WR, dynamic fraction, confidence adjust, stake limits, per-strategy, fallback. Cubre: R10.
- [ ] T10 — Update scanner to use Kelly per-trade: call `kelly_sizer.calculate()` with ML confidence, use returned stake as amount. Cubre: R9.
- [ ] T11 — Add fallback logic: if LightGBM not available, use basic Kelly without confidence. Cubre: R8.
- [ ] T12 — Run full test suite, verify no regressions. Cubre: R10.
- [ ] T13 — Commit, push, update `feature_list.json` status to done.
