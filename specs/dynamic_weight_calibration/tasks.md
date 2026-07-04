# Tasks — dynamic_weight_calibration

- [x] T1 — Crear `src/weight_calibrator.py` con clase `WeightCalibrator`:
  `__init__`, `load_trades`, `_hour_bucket`, `_determine_vol_regimes`,
  `_vol_regime`, `_recompute_score`, `_sharpe`, `_optimize_weights`,
  `calibrate`.
  Cubre: R1, R2, R5, R6.

- [x] T2 — Implementar exportación a JSON y carga desde JSON:
  `export_weights`, `load_weights` (staticmethod), `select_weights`.
  Cubre: R3, R4.

- [x] T3 — Integrar carga de pesos calibrados al inicio del bot en
  `src/consolidation_bot.py`.
  Cubre: R4.

- [x] T4 — Crear `tests/test_weight_calibrator.py` con base SQLite en
  memoria (datos sintéticos). Verificar: estructura JSON, export/load
  roundtrip, calibración con datos mínimos, selección de pesos por grupo.
  Cubre: R1, R2, R3, R5, R6.
