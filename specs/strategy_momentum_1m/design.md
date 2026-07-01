# Design — strategy_momentum_1m

## Reglas de detección

1. Lookback de 10 velas para `avg_body`
2. Última vela: `body >= 1.5 × avg_body`
3. CALL: vela alcista (`close > open`) y cierre en tercio superior (`>= 66%` del rango)
4. PUT: vela bajista (`close < open`) y cierre en tercio inferior (`<= 33%` del rango)
5. `strength` normalizada en `[0, 1]` según exceso de cuerpo sobre umbral

## Integración scanner

Tras evaluar STRAT-B y antes del filtro de consolidación 5m:

- `detect_momentum_1m(candles_1m)`
- Si hay señal: crear `CandidateEntry` con zona pseudo y score base `strength * 100`
- Añadir a `candidates` con metadata `STRAT-MOMENTUM`

## Fuera de alcance

- Auto-trade independiente (como STRAT-B); entra al pipeline de scoring común.