# Design — Entry Intelligence Agent (lightgbm_scorer, alcance ampliado)

> **Feature ID:** 18
> **Architecture layer:** Analysis (scanner) + ML module
> **Principio:** el ÚNICO indicador técnico es el estocástico; el resto son
> matemáticas/geometría de las velas. El modelo descubre relaciones solo.

---

## Módulos (ya existen, se extienden)

| Módulo | Rol |
|--------|-----|
| `src/ml_scorer.py` | `MLScorer`: load/predict/train/save/feature_importance (YA hecho, T1–T9) |
| `src/ml_features.py` | Extracción de features puras, sin I/O (SE EXTENDERÁ con geometría) |
| `src/entry_scorer.py` | `score_candidate()` — SE CABLEARÁ el score ML como capa extra (T10–T13) |
| `scripts/train_lightgbm.py` | Entrenamiento desde black box (YA hecho) |
| `scripts/agent_live.py` o cron | Gatilla auto-retrain continuo (T14–T16) |

---

## Feature Schema (ensanchado)

```python
FEATURE_NAMES = [
    # ── Estocástico (único indicador) por TF ──
    "stoch_m15_zone", "stoch_m15_delta", "stoch_m15_bull", "stoch_m15_bear",
    "stoch_m5_zone",  "stoch_m5_delta",  "stoch_m5_bull",  "stoch_m5_bear",
    "stoch_m1_zone",  "stoch_m1_delta",  "stoch_m1_bull",  "stoch_m1_bear",

    # ── Geometría/matemáticas de las velas (OFFLINE desde candles_*) ──
    "math_hurst", "math_r_squared", "math_angle_deg", "math_squeeze", "math_composite",
    "body_dir",          # signo (close-open) de vela entrada vs direction
    "body_ratio",        # |c-o| / range de la vela de entrada
    "opp_wick_ratio",    # mecha opuesta / range (rechazo vs convicción)
    "entry_extreme_pos", # dónde cerró en el rango local (extremo=alto)
    "pre_trend_slope",   # pendiente de cierres N velas previas
    "compression",       # rango ventana / rango histórico
    "fractal_align",     # alineación fractal M5 vs direction

    # ── Contexto ──
    "direction", "payout", "duration_sec",
    "hour_utc", "dow",
    "asset_oh_<TOP_N>",  # one-hot de los top-N activos OTC más frecuentes
]
```

---

## Extracción geométrica (OFFLINE, sin hot path)

```python
def extract_geometry(candles: list[Candle], direction: str) -> dict:
    """Calcula geometría de la ventana pre-entry desde velas ya guardadas."""
    if not candles:
        return {k: 0.0 for k in GEOM_KEYS}
    last = candles[-1]
    rng = (last.high - last.low) or 1e-9
    body = last.close - last.open
    body_dir = 1.0 if (body > 0) == (direction == "CALL") else 0.0
    body_ratio = abs(body) / rng
    # mecha opuesta a la dirección del trade
    if direction == "CALL":
        opp_wick = last.high - max(last.open, last.close)
    else:
        opp_wick = min(last.open, last.close) - last.low
    opp_wick_ratio = max(0.0, opp_wick) / rng
    # posición de cierre en el rango (0=abajo,1=arriba)
    entry_extreme_pos = (last.close - last.low) / rng
    closes = [c.close for c in candles[-WINDOW:]]
    pre_trend_slope = _slope(closes)
    window_r = max(c.high for c in candles[-WINDOW:]) - min(c.low for c in candles[-WINDOW:])
    hist_r = max(c.high for c in candles) - min(c.low for c in candles) or 1e-9
    compression = window_r / hist_r
    return {
        "body_dir": body_dir, "body_ratio": body_ratio,
        "opp_wick_ratio": opp_wick_ratio, "entry_extreme_pos": entry_extreme_pos,
        "pre_trend_slope": pre_trend_slope, "compression": compression,
        "fractal_align": 0.0,  # lo llena evaluate_strat_f / scanner
    }
```

`ml_features.extract_features` se amplía para: leer `candles_1m/5m/15m` (JSON)
de `scan_candidates`, llamar `extract_geometry`, y unir con estocástico +
contexto. NO se toca el scanner en vivo para esto.

---

## Integración en scanner (capa extra)

En `entry_scorer.score_candidate()`, tras el scoring estático:

```python
if ML_ENABLED and ml_scorer.is_available():
    feats = extract_features(strategy_json_con_candles)
    conf = ml_scorer.predict(feats)
    if conf is not None:
        candidate.score = round(candidate.score * (0.7 + 0.3 * conf), 1)
        log.info(f"[ML] confidence={conf:.2f} → score {candidate.score}")
```

`ML_ENABLED` arranca `False` (bot opera igual hasta que se encienda en demo).

---

## Auto-retrain continuo

Un gatillo (cron 6h o hook post-trade daemon en `agent_live`) cuenta trades
nuevos resueltos desde el último `trained_at`; si >100, llama
`MLScorer.train()` (walk-forward, guarda metadata, recarga en memoria). El
scanner usa el modelo fresco en la próxima predicción.

---

## Alternativas descartadas

1. **RSI/ADX/ATR/bandas:** descartadas por decisión del usuario — solo
   estocástico + geometría/matemáticas.
2. **Reglas hardcodeadas de velas:** descartadas — el modelo debe descubrir
   las relaciones (feature_importance explica qué encontró).
3. **LSTM/online learning:** descartados (batch walk-forward es más seguro y
   validable; el repo ya tiene LightGBM).
