# Tasks — Entry Intelligence Agent (lightgbm_scorer, alcance ampliado)

> **Feature ID:** 18
> **Estado:** spec_ready (esperando aprobación humana)
> **Principio:** solo estocástico + geometría/matemáticas de velas. Sin RSI/ADX/ATR/bandas.
> **Nombre sugerido:** Entry Intelligence Agent

---

## Phase 1: Data & Features (YA PARCIAL — completar geometría)

- [x] T1 — `lightgbm`, `scikit-learn`, `joblib` en requirements.txt. (R1)
- [x] T2 — `src/ml_features.py` con `extract_features()`, `extract_from_db_row()`, `validate_features()`. (R2 base)
- [x] T3 — `tests/test_ml_features.py` (10+ tests). (R2, R10)
- [x] T4 — `src/ml_scorer.py` con `MLScorer` (init/predict/is_available/save/load). (R3, R4)
- [x] T5 — `tests/test_ml_scorer.py` (predict mock, fallback, edge cases). (R3, R4, R10)
- [x] T2b — Ampliar `ml_features.py`: `extract_geometry_from_candles()` (body_dir, body_ratio, opp_wick_ratio, entry_extreme_pos, pre_trend_slope, compression_geom, fractal_align) + `extract_features_full(row)` que lee `candles_1m/5m/15m` + stoch_m5/m1 OFFLINE desde scan_candidates. (R2, R11)
- [x] T2c — Ensanchar `FEATURE_NAMES` (estocástico M15/M5/M1 + geometría + contexto hour_utc/dow/asset_id/duration_norm/vol_proxy). (R2)
- [x] T3b — Tests de geometría con velas mock (cuerpo a favor/en contra, mecha opuesta, extremo) en `tests/test_entry_intelligence.py`. (R2, R10, R11)

## Phase 2: Training Pipeline (YA HECHO, validar)

- [x] T6 — `train()` con walk-forward. (R1, R5)
- [x] T7 — `scripts/train_lightgbm.py`. (R1, R9)
- [x] T8 — `feature_importance()` + metadata. (R9)
- [x] T9 — `tests/test_ml_training.py` (sintético). (R5, R10)

## Phase 3: Integration (HECHO)

- [x] T10 — `ml_confidence` + `ml_adjusted_score` en `CandidateEntry` vía `setattr` en `entry_scorer._apply_ml_layer` (sin ALTER TABLE; el scorer las adjunta en runtime y el black_box_recorder puede leerlas). (R8)
- [x] T11 — Cablear `MLScorer.predict()` en `score_candidate()` detrás de `ML_ENABLED`: `final = base * (0.7 + 0.3 * confidence)`. (R7)
- [x] T12 — Log `[ML] confidence=X.XX adjust=+/-Y.Y` en `_apply_ml_layer`. (R8)
- [x] T13 — Test de cableado (ML off = score base; ML on sin modelo = fallback limpio) en `tests/test_entry_intelligence.py`. (R7, R10)

## Phase 4: Continuous Retraining (HECHO)

- [x] T14 — `maybe_retrain()`: cuenta trades nuevos resueltos desde `last_retrain.json`; retrain si >100 (o `--force`). (R6)
- [x] T15 — `run_training` entrena a temp; `maybe_retrain` compara F1 nuevo vs previo (conserva mejor) y recarga vía `MLScorer` al predicar. (R6)
- [x] T16 — `tests/test_entry_intelligence.py` (guard bloquea <MIN_TRADES; force entrena; rollback de txn abortada). (R6, R10)

## Phase 5: Validation & Close (PENDIENTE — requiere datos + activar ML_ENABLED en demo)

- [ ] T17 — `scripts/entry_intelligence_retrain.py --force` sobre black box real; reporte en `progress/ml_validation.md` + `feature_importance()` (QUÉ descubrió el modelo). (R5, R9)
- [ ] T18 — Smoke test bot con `ML_ENABLED=True` en demo (validar que la capa extra ajusta el score sin romper el hot path). (R7)
- [ ] T19 — `docs/EVOLUTION_PLAN.md` status Feature 18 = done (renombrado Entry Intelligence Agent).
- [ ] T20 — Commit, push, `feature_list.json` status = done.
