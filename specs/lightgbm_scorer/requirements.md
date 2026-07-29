# Requirements — Entry Intelligence Agent (lightgbm_scorer, alcance ampliado)

> **Feature ID:** 18
> **Status:** spec_ready
> **Depends on:** None (data already collecting in scan_candidates)

---

## Contexto / Alcance (Ruben 2026-07-24)

El objetivo NO es un "filtro de velas con reglas predefinidas". Es un agente de
aprendizaje estadístico que **descubre por sí mismo** qué configuraciones del
mercado tienen mayor probabilidad de éxito, y emite un **Entry Quality Score**
(0–1) que el scanner consulta como CAPA EXTRA antes de abrir (sin reemplazar la
estrategia STRAT-F). El modelo aprende de TODAS las operaciones resueltas y
mejora el winrate con el tiempo.

**Restricción de features (decisión del usuario):** el ÚNICO indicador técnico es
el **estocástico** (M15/M5/M1, ya capturado). Todo lo demás son **matemáticas y
geometría del mercado** derivadas de las velas OHLC (cuerpo, mecha, rango,
pendiente, compresión, fractal, posición en el extremo). **NO** se usan
RSI/ADX/ATR/bandas externas. El modelo debe encontrar relaciones (p.ej.
"estocástico en 18 + pendiente de las últimas 7 velas positiva + bandas
abriéndose → 71%") sin que se las programemos.

---

## R1 — Model Training Pipeline

CUANDO hay al menos 500 trades resueltos (outcome IN ('WIN','LOSS')) en la black
box, EL sistema DEBE poder entrenar un modelo LightGBM y guardarlo en
`data/models/lightgbm_v1.pkl`.

---

## R2 — Feature Extraction (estocástico + geometría + contexto)

CUANDO se entrena o predice, EL sistema DEBE extraer features de tres familias:

1. **Estocástico (M15/M5/M1):** zone (1–5), score_delta, bullish_cross,
   bearish_cross — por cada TF. (Único indicador técnico, ya grabado en
   `scan_candidates.stoch_m15/stoch_m5/stoch_m1`.)
2. **Geometría/matemáticas de las velas (OFFLINE, desde `candles_1m/5m/15m` ya
   guardadas en `scan_candidates`):**
   - `body_dir` — signo de (close−open) de la vela de entrada vs dirección del trade.
   - `body_ratio` — |close−open| / rango de la vela de entrada.
   - `opp_wick_ratio` — mecha opuesta a la dirección / rango (rechazo vs convicción).
   - `entry_extreme_pos` — dónde cerró la vela de entrada en el rango local
     (cerca del extremo = entró en extremo, con/sin cuerpo a favor).
   - `pre_trend_slope` — pendiente de los cierres de las N velas previas.
   - `compression` — rango de la ventana / rango histórico (estrangulamiento).
   - `fractal_align` — alineación del fractal M5 con la dirección.
   - `math_quality` ya existente: hurst, r_squared, angle_deg, squeeze, composite.
3. **Contexto:** direction (CALL=1/PUT=0), payout, duration_sec, hour_utc,
   day_of_week, asset (one-hot de los top-N activos OTC más frecuentes).

NO se añaden RSI/ADX/ATR/bandas ni ningún indicador externo.

---

## R3 — Prediction Output

CUANDO el modelo está cargado y recibe un candidato, EL sistema DEBE devolver
`confidence` float 0.0–1.0 (1.0 = máxima confianza de WIN).

---

## R4 — Model Fallback

SI el modelo no existe o no carga, EL sistema DEBE devolver `confidence = None`
y usar el scoring estático actual (sin cambios al pipeline).

---

## R5 — Walk-Forward Validation

CUANDO se entrena, EL sistema DEBE usar walk-forward (split temporal 80/20, NO
random) y reportar accuracy/precision/recall/F1. El modelo nuevo compite contra
el anterior por F1.

---

## R6 — Continuous Retraining

CUANDO el número de trades nuevos resueltos desde el último entrenamiento supera
100, EL sistema DEBE reentrenar automáticamente (desde los trades resueltos de
`scan_candidates`), comparar F1 con el anterior y conservar el mejor. El modelo
se recarga en memoria para que `predict()` lo use de inmediato.

---

## R7 — Confidence Integration in Scanner (capa extra, NO reemplazo)

CUANDO el scanner evalúa un candidato STRAT-F y hay modelo cargado, EL sistema
DEBE ajustar el score final como capa extra:
`final_score = base_score * (0.7 + 0.3 * confidence)`.
La estrategia STRAT-F NO se reemplaza; el score ML solo modula la priorización.

---

## R8 — Confidence Logging

CUANDO se predice, EL sistema DEBE loggear `[ML] confidence=0.XX para ASSET en
DIRECTION`.

---

## R9 — Model Metadata + Explainability

CUANDO se guarda un modelo, EL sistema DEBE guardar `data/models/lightgbm_meta.json`
con trained_at, n_samples, accuracy, precision, recall, f1 y **feature_importance**
(diccionario) — para que el agente "explique" qué relaciones descubrió (p.ej.
"estocástico 18 + pendiente + compresión → alta WR").

---

## R10 — Tests

Los tests DEBEN cubrir extracción de features (geométricas desde velas mock +
estocástico + contexto), predicción con modelo mock, fallback, walk-forward con
datos sintéticos, integración con scanner (mock), y edge cases.

---

## R11 — Extracción OFFLINE (sin tocar el hot path del bot)

Las features geométricas SE CALCULAN OFFLINE desde `candles_1m/5m/15m` ya
persistidas en `scan_candidates`. NO se añade I/O ni cómputo al ciclo del scanner
en vivo; el bot ya guarda esas velas. El entrenamiento/inferencia corren fuera
del hot path (script / cron / hook post-trade daemon).
