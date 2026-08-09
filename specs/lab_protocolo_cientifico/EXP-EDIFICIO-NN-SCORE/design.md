# EXP-EDIFICIO-NN-SCORE — Diseño técnico

## 1. Objetivo operativo

Medir si un modelo tabular (LightGBM) sobre features **ya existentes del Edificio** mejora:
- el ranking de candidatos (AUC),
- el win-rate del top-k,
- la calibración de probabilidad,

respecto al score que el Edificio ya usa hoy.

## 2. Pipeline

```
candidatos Edificio (o generator de zonas+señales)
→ features whitelist (solo pasado)
→ label (WIN/LOSS real o clean_N)
→ split temporal
→ baseline = score Edificio
→ train LightGBM en TRAIN
→ evaluate OOS (AUC, top-k WR, lift, IC95%, calibración)
→ summary + protocol_frozen
→ stop
```

## 3. Features (whitelist — ajustar a lo que realmente expone el código)

Ejemplos típicos (confirmar en código / logs):
- zone: strength_pct, line_thickness, efficacy, impact_velocity, touch_count, bounce_rate
- stochastic: K, D, kd_sep, sticky_bars, cross_flag
- edificio: brake_flag, score_actual, direction
- contexto: atr_ratio, hour (si ya se usa)

Cualquier feature fuera de la lista documentada en protocol_frozen queda prohibida en este EXP.

## 4. Modelo

- **Primero:** LightGBM (o XGBoost / sklearn HistGradientBoosting) sobre tabla de features.
- Hiperparámetros fijos y conservadores (max_depth bajo, regularización, early stopping).
- **No** empezar por LSTM/Transformer hasta que el tabular demuestre lift OOS.
- Comparación obligatoria: modelo vs score_actual del Edificio en el mismo TEST.

## 5. Métricas

| Métrica | Dónde | Uso |
|---------|-------|-----|
| AUC | TRAIN y TEST | H1 |
| Win-rate global | TRAIN y TEST | contexto |
| Win-rate top 20% / 30% | TEST | H2 |
| Lift vs baseline top-k | TEST + IC95% bootstrap | H2 |
| ECE / reliability | TEST | H3 |
| Gap AUC TRAIN−TEST | — | alerta overfit |

### Tabla resumen OOS (obligatoria en summary.txt)

```
| Métrica                    | Score Edificio | Modelo     | Diff / Lift | IC95%           | n    |
|----------------------------|----------------|------------|-------------|-----------------|------|
| AUC OOS                    | …              | …          | …           | […]             | …    |
| WR global OOS              | …              | …          | …           | […]             | …    |
| WR top 20% OOS             | …              | …          | …           | […]             | …    |
| WR top 30% OOS             | …              | …          | …           | […]             | …    |
| Lift top 20% vs baseline   | —              | …          | …           | […]             | …    |
| Lift top 30% vs baseline   | —              | …          | …           | […]             | …    |
| ECE OOS (calibración)      | …              | …          | …           | —               | —    |
| Gap AUC TRAIN−TEST         | —              | …          | …           | —               | —    |
```

IC95% de rates: Wilson o bootstrap. IC95% de lift: bootstrap.

## 6. Outputs obligatorios

```
reports/EXP-EDIFICIO-NN-SCORE/
  summary.txt
  protocol_frozen.json
  baseline_metrics.json
  model_metrics.json
  topk_table.csv          # con IC95%
  calibration_oos.csv     # o plot data
  feature_importance.csv

progress/current.md
agent/HANDOFF.md
```

## 7. Relación con EXP-POI-STOCH

EXP-POI-STOCH refutó el patrón “POI + estocástico saludable / separación excesiva” como edge robusto OOS.  
Este experimento **no** reutiliza esa hipótesis como feature estrella.  
Solo usa lo que el Edificio ya calcula. Si el score del Edificio ya incluye componentes de zona y estocástico, el modelo puede reponderarlos; no se añaden reglas refutadas a mano.

## 8. Criterio de parada

Cuando summary.txt tenga veredictos H1/H2/H3 y los reportes estén escritos:
- actualizar estado,
- commit solo de este EXP,
- **no** proponer merge al bot,
- parar y esperar nueva orden.
