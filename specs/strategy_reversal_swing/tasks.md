# Tasks — strategy_reversal_swing

- [x] T1 — Crear `src/strat_reversal_swing.py` con `detect_reversal_swing()`. Cubre: R1, R2, R3, R4.
- [x] T2 — Añadir constantes `STRAT_REVERSAL_SWING_ENABLED`, `STRAT_REVERSAL_SWING_LOOKBACK`, `STRAT_REVERSAL_SWING_MAX_SWINGS`, `STRAT_REVERSAL_SWING_PROXIMITY_TOLERANCE`, `STRAT_REVERSAL_SWING_MIN_WICK_RATIO` y `STRAT_REVERSAL_SWING_MIN_STRENGTH` en `config.py`. Cubre: R5.
- [x] T3 — Integrar reversal_swing en `scanner.py` (bloque post-momentum, pre-STRAT-A) con creación de `CandidateEntry` y `score_candidate()`. Cubre: R5, R6.
- [x] T4 — Crear `tests/test_strat_reversal_swing.py` con casos: señal CALL en soporte, señal PUT en resistencia, mecha grande vs pequeña, sin señal si no hay toque. Cubre: R7.
- [x] T5 — Verificar que `python -m pytest tests/ -v` pasa y `.\init.ps1` termina en verde.
