# Tasks — Telegram Alerts

## Phase 1: Spec
- [x] T1 — Create `specs/telegram_alerts/requirements.md`. Cubre: R1–R10.
- [x] T2 — Create `specs/telegram_alerts/design.md`. Cubre: R1–R10.

## Phase 2: Implementation
- [x] T3 — Create `src/alerter.py` with `TelegramAlerter` class. Cubre: R1, R2, R3, R9, R10.
- [x] T4 — Integrate alerter in `massaniello_risk.py` (session_complete + losing_streak). Cubre: R4, R5.
- [x] T5 — Integrate alerter in `executor.py` (stop_loss). Cubre: R7.
- [x] T6 — Integrate alerter in `consolidation_bot.py` (connection_lost). Cubre: R6.

## Phase 3: Tests
- [x] T7 — Create `tests/test_alerter.py` with 12 tests. Cubre: R8, R10.

## Phase 4: Verify
- [x] T8 — Run `python -m pytest tests/test_alerter.py -v` (all green — 11/11).
- [x] T9 — Run `python -m pytest tests/ -v` (224 passed, 14 pre-existing failures in scanner.py - no regressions introduced).
