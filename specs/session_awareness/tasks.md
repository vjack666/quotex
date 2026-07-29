# Tasks — session_awareness

> **Feature ID:** 21
> **Estimated effort:** 2-3 days
> **Order:** Execute sequentially

---

- [ ] T1 — Create `src/session_awareness.py` with `detect_session()`, `get_session_config()`, `should_block()`, `get_min_score()`, `get_current_session()`, `get_effective_min_score()`. Cubre: R1, R2, R3, R4.
- [ ] T2 — Add SESSION_* constants to `src/config.py`. Cubre: R7.
- [ ] T3 — Create `tests/test_session_awareness.py` with 10+ tests: session detection, score adjust, off-hours block, transition logging, disabled fallback, hour boundaries. Cubre: R8.
- [ ] T4 — Integrate session awareness in `src/scanner.py`: detect session at scan start, use effective_min_score, log session info. Cubre: R3, R5, R6.
- [ ] T5 — Add session transition detection: compare current session with previous, log if changed. Cubre: R6.
- [ ] T6 — Run full test suite, verify no regressions. Cubre: R8.
- [ ] T7 — Commit, push, update `feature_list.json` status to done.
