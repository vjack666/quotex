# Tasks — smart_order_place

- [x] T1 — Config `ORDER_FAIL_QUARANTINE_CYCLES` (default 5). Cubre: R7
- [x] T2 — Executor: prewarm trade_client before/during open wait; set `last_order_attempt` on waiting/sending/accepted/failed; quarantine cycles on hard fail; optional `skip_open_wait`. Cubre: R1, R2, R3, R4, R7
- [x] T3 — Scanner alt loop: pass `skip_open_wait=True` after first fail; log real reject reason. Cubre: R2, R3
- [x] T4 — Hub server `_enrich_with_bot` exposes `last_order_attempt`. Cubre: R5
- [x] T5 — Hub `index.html` shows last order attempt line. Cubre: R6
- [x] T6 — Tests for prewarm/skip path + last_order_attempt + enrich (mocks). Cubre: R9
- [x] T7 — Run new tests green; document in `progress/impl_smart_order_place.md`. Cubre: R8, R9
