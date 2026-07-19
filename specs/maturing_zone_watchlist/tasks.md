# Tasks — maturing_zone_watchlist

> One feature. Do not edit R3 formula in `strat_fractal.py`. TDD: pure store first.

- [x] T1 — Create `src/maturing_watchlist.py` (`MaturingEntry`, `MaturingWatchlist`, `is_r3_young_skip`, counters, cap/TTL/max age). Cubre: R1, R4, R8, R9, R11, R13.

- [x] T2 — `tests/test_maturing_watchlist.py` full lifecycle. Cubre: R1, R8, R9, R11, R13, R14.

- [x] T3 — Config flags in `src/config.py` (+ env mode). Cubre: R2.

- [x] T4 — Attach `MaturingWatchlist` on `ConsolidationBot`; wire scanner: capture R3 young; re-eval active; promote live/shadow; drop invalid. Cubre: R3, R5, R6, R7, R8, R12.

- [x] T5 — Flush maturing rows to `strat_f_panel` / state; hub UI count or table. Cubre: R10.

- [x] T6 — `tests/test_maturing_watchlist_scanner.py` mocks. Cubre: R5, R6, R7, R14.

- [x] T7 — Run targeted pytest green; write `progress/impl_maturing_zone_watchlist.md` R→test map.

- [x] T8 — Update `feature_list.json` status path notes; PROJECT_STATE brief; skill registry if project skill added.
