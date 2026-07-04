# Design — strategy_reversal_swing

## Módulo

`src/strat_reversal_swing.py` — función única:

```python
def detect_reversal_swing(candles_1m: list[Candle]) -> Optional[tuple[str, float]]:
```

## Detección de swing levels

1. Lookback de `SWING_LOOKBACK = 12` velas 1m.
2. **Swing high**: vela `i` donde `high[i] > high[i-1]` y `high[i] > high[i+1]`
   (confirmación izquierda y derecha).
3. **Swing low**: vela `i` donde `low[i] < low[i-1]` y `low[i] < low[i+1]`.
4. Se mantienen los últimos `MAX_SWINGS = 5` swing highs y swing lows como
   niveles dinámicos de resistencia y soporte respectivamente.

## Medición de mechas (wick)

Dada una vela:
- **Upper wick** = `high - max(open, close)`
- **Lower wick** = `min(open, close) - low`
- **Wick total** = `range - body`
- **Wick ratio** = upper wick / range (para PUT) o lower wick / range (para CALL)

## Tolerancia de proximidad

Un precio toca un nivel si `abs(level - touch_price) / level <= 0.001` (0.1%).
- PUT: el `high` de la vela actual debe estar dentro de tolerancia de un swing high.
- CALL: el `low` de la vela actual debe estar dentro de tolerancia de un swing low.

## Confirmación de mecha

Además del toque, la mecha opuesta debe ser significativa:
- PUT: `upper_wick / range >= MIN_WICK_RATIO` (default 0.4, 40% del rango).
- CALL: `lower_wick / range >= MIN_WICK_RATIO`.

Esto descarta velas que cerraron cerca del extremo (sin rechazo real).

## Cálculo de strength

1. `avg_wick_size` = media del upper wick (PUT) o lower wick (CALL) en las
   últimas `SWING_LOOKBACK` velas.
2. `raw_strength = wick_size / avg_wick_size` (piso en 0.0, techo en 2.0).
3. `strength = min(raw_strength, 1.0)` normalizado a `[0, 1]`.

## Integración en scanner.py

Después del bloque momentum (~línea 1229), antes del bloque STRAT-A (~línea 1231):

```python
if not _runtime_config.STRAT_A_ONLY and STRAT_REVERSAL_SWING_ENABLED:
    swing_hit = detect_reversal_swing(candles_1m)
    if swing_hit:
        direction, strength = swing_hit
        pseudo_zone = ConsolidationZone(
            zone_id=f"swing-{asset}-{candles_1m[-1].ts}",
            support=candles_1m[-1].low,
            resistance=candles_1m[-1].high,
            strength=strength,
        )
        candidate = CandidateEntry(
            asset=asset,
            payout=payout,
            zone=pseudo_zone,
            direction=direction,
            candles=candles_1m,
            score=0.0,
            score_breakdown={},
            reversal_pattern="swing_rejection",
            reversal_strength=strength,
            reversal_confirms=True,
            mode=SignalMode.REBOUND,
            _strategy_origin="STRAT-REVERSAL-SWING",
        )
        candidate = score_candidate(candidate)
        candidates.append(candidate)
```

## Constantes en config.py

```python
STRAT_REVERSAL_SWING_ENABLED = True
STRAT_REVERSAL_SWING_SWING_LOOKBACK = 12
STRAT_REVERSAL_SWING_MAX_SWINGS = 5
STRAT_REVERSAL_SWING_PROXIMITY_TOLERANCE = 0.001
STRAT_REVERSAL_SWING_MIN_WICK_RATIO = 0.4
STRAT_REVERSAL_SWING_MIN_STRENGTH = 0.3
```

## Alternativas consideradas

| Alternativa | Motivo de rechazo |
|---|---|
| RSI divergencia | Menos determinista; señal depende de ventana y umbral; más difícil de testear con datos sintéticos |
| Soportes/resistencias fijos (números redondos) | No se adapta a la volatilidad del activo OTC |
| Bandas de Bollinger | Requiere mantener estado (media móvil, desviación), viola R4 |

**Decisión**: swing levels dinámicos — deterministas, puros, fáciles de testear.

## Scoring

Reutiliza `score_candidate()` con los pesos existentes de `SignalMode.REBOUND`.
No se añade lógica de scoring específica.

## Fuera de alcance

- Confirmación multi-timeframe (ej. 5m para tendencia)
- Análisis de volumen
- Auto-trade independiente (entra al pipeline de scoring común como STRAT-MOMENTUM)
