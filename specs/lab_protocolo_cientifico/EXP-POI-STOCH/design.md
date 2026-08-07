# EXP-POI-STOCH — Diseño técnico completo

## 1. Definición operativa del patrón buscado

### 1.1 POI (zona)
- Banda de precio derivada de:
  - Swing highs/lows o
  - Clustering de toques (método ya usado en zone_strength / zone_ia).
- Grosor mínimo: efficacy ≥ poi_min_efficacy (congelado).
- La zona debe existir **antes** del retorno (sin look-ahead).

### 1.2 Retorno
- Precio (low o high según dirección) entra en la banda de la zona.
- Se registra el open de la vela M15 en la que ocurre el toque/retorno.

### 1.3 Estocástico “saludable”
Definición a priori (ejemplo, ajustar solo en protocol_frozen antes de correr):
- No sticky: menos de 3 velas consecutivas con K ≤ 20 o K ≥ 80.
- Separación moderada: p30 ≤ |K−D| ≤ p70 de la distribución histórica de |K−D| en retornos a zona
  (o valores fijos documentados: ej. 5 ≤ |K−D| ≤ 18).

### 1.4 Estocástico “excesivo” (H2)
- |K−D| ≥ p85 (o valor fijo alto documentado).

### 1.5 Entrada
- Open de la vela M15 del retorno (o la siguiente si el toque ocurre intra-vela; documentar la regla exacta).

## 2. Features a extraer por evento

**Zona**
- level, band_width, efficacy, touch_count_prev, bounce_rate_prev, last_touch_ago

**Precio en el retorno**
- dist_to_level (normalizado por ATR), body, range, direction_of_approach

**Estocástico**
- K, D, kd_sep = |K−D|, sticky_bars, slope_K_3, slope_D_3

**Contexto**
- n_osc_recent (si se reutiliza detector de Fase A), atr_ratio, session_hour (opcional)

**Labels**
- clean_4, clean_8 (bool)
- next_retrace (bool)
- move_fwd_4, move_fwd_8 (float, para análisis continuo)

## 3. Pipeline de datos

```
load M15 (pares disponibles)
→ compute stochastic (K, D)
→ detect zones (past-only)
→ detect returns to zones
→ attach stoch features at return open
→ compute forward labels
→ split temporal TRAIN / TEST
→ tests H1 + H2 (FDR)
→ if n_train ≥ 300: train NN / boosting → evaluate OOS
→ write immutable reports
```

## 4. Neural net / modelo de secuencia (H3)

**Opción A (recomendada empezar):** Gradient Boosting / LightGBM sobre features tabulares del evento.  
Rápido, interpretable, menos overfit.

**Opción B (si A funciona):** LSTM o Transformer pequeño sobre ventana de 12–16 velas (OHLCV normalizado + K/D + mask de zona).

**Target:** probabilidad de clean_bounce_8 (o binary).

**Baseline obligatorio:** la regla fija de H1 (POI quality + healthy kd_sep).  
La red solo se considera útil si supera a esa regla en OOS.

**Regularización:** max_depth bajo, subsample, early stopping sobre validation temporal interna del TRAIN.

## 5. Outputs obligatorios

```
reports/EXP-POI-STOCH/
  summary.txt
  protocol_frozen.json
  h1_results.csv
  h2_results.csv
  h3_metrics.json          (si aplica)
  feature_importance.csv   (si aplica)
  events_sample.parquet    (muestra de eventos para auditoría)

progress/current.md        ← actualizar veredicto
agent/HANDOFF.md           ← actualizar estado
```

## 6. Orden de ejecución hands-free (para el agente)

```
1. Leer hypothesis.md + risks.md + validation.md + este design.md
2. Escribir protocol_frozen.json con todos los umbrales fijos
3. Ejecutar extracción + tests H1/H2
4. Si n suficiente → entrenar y evaluar H3
5. Escribir summary.txt con veredictos claros (ACEPTADA/REFUTADA/INCONCLUSA)
6. Actualizar progress/current.md y HANDOFF.md
7. Commit solo archivos de este EXP (no git add -A)
8. Parar. No preguntar. No proponer cambios al Edificio.
```

## 7. Nota sobre las capturas del Trader-Humano

Las dos imágenes (EUR/CHF) sirven **únicamente** como especificación cualitativa del patrón visual deseado.  
No se usan como labels ni como muestra de entrenamiento.  
El experimento busca el patrón de forma exhaustiva en todo el histórico disponible.
