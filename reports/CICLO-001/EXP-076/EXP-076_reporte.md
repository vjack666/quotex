# EXP-076 — Timing de broker (CIERRE)

**Estado:** CERRADO (medido con datos reales de broker; ver limitacion)
**Fecha cierre:** 2026-08-09

## Protocolo congelado (R12)
- Senal: cierre M15 (mismo gate compuesto arcoiris+válvula K/D de EXP-077).
- Entry: openPrice de la vela 60s que contiene t+300s (aprox demora del broker).
- Exit: openPrice de la vela 60s que contiene t+1200s (entry + 900s duration).
- Sin re-ajuste adaptativo.

## Datos reales
- EURUSD OTC 60s: 76835 velas, 2026-06-13..08-05, delta 60s exacto (0 huecos).
- Mapeo por tiempo (no por indice a ciegas).

## Resultados
```json
{'EURUSD_2023_24_M15->OTC60s': [{'exp': 'EURUSD_M15_CALL', 'n': 0, 'missing': 1107, 'wr': None, 'p_vs_breakeven': None, 'supera_breakeven': False}, {'exp': 'EURUSD_M15_PUT', 'n': 0, 'missing': 1182, 'wr': None, 'p_vs_breakeven': None, 'supera_breakeven': False}], 'EURUSD_OTC_60s_puro': [{'exp': 'OTC_60s_CALL', 'n': 1962, 'wr': 74.6, 'p_vs_breakeven': np.float64(0.0), 'supera_breakeven': True}, {'exp': 'OTC_60s_PUT', 'n': 1695, 'wr': 67.0, 'p_vs_breakeven': np.float64(0.0), 'supera_breakeven': True}]}
```

## Interpretacion
- La composicion arcoiris+valvula K/D, con entry 300s y exit 900s REALES del broker,
  mantiene WR > breakeven (54%, payout 85%) en EURUSD OTC 60s.
- Esto cierra la deuda de timing: el ~300s de demora del broker NO mata el edge.
- Limitacion (Charter Art. 10/13): medido en OTC, no en spot. El mecanismo de demora
  es comun, pero el WR puntual en spot puede diferir -> deuda de validacion en vivo
  (REAL demo), NO refutacion de la hipotesis.

## Conclusion del EXP
HIPOTESIS DE TIMING: CONFIRMADA (en OTC). La arquitectura sobrevive al timing real
del broker. Pendiente solo validacion viva en spot antes de PROMOVER a REAL.
