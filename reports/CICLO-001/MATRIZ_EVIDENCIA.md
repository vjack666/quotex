# MATRIZ DE EVIDENCIA — CICLO-001

**Hipótesis:** ¿La arquitectura compuesta (arcoíris + válvula K/D como gates del embudo P1→P2→P3) produce contratación robusta con n combinado suficiente?

| EXP | Resultado | Peso | Nota |
|---|---|---|---|
| EXP-076 timing broker | CERRADO | ALTO | medido en OTC 60s; WR 67-75% > breakeven; edge sobrevive 300s demora |
| EXP-077 composición | VER | ALTO | n combinado por dataset |
| EXP-078 OOS externo | VER | ALTO | EURUSD 2012–2022 |
| EXP-079 frecuencia | VER | ALTO | n combinado |
| EXP-080 OTC | VER | MEDIO | EURUSD OTC 60s |

## Resumen numérico (EXP-077 composición combinada, WR i+1/i+2 close M15)
- EURUSD_2023_24_COMP_CALL: n=2599 WR=61.2
- EURUSD_2023_24_COMP_PUT: n=2765 WR=60.8
- EURUSD_OOS_2012_2022_COMP_CALL: n=16176 WR=60.0
- EURUSD_OOS_2012_2022_COMP_PUT: n=17053 WR=59.4
- XAUUSD_COMP_CALL: n=22610 WR=61.1
- XAUUSD_COMP_PUT: n=19168 WR=59.3

## OTC (EXP-080 composición, M15)
- OTC_COMP_CALL: n=5196 WR=60.9
- OTC_COMP_PUT: n=4585 WR=61.0

## EXP-076 cierre (timing real broker, EURUSD OTC 60s, entry openPrice +300s, exit +900s)
- OTC_60s_CALL: n=1962 WR=74.6 (p≈0 vs breakeven 54%)
- OTC_60s_PUT: n=1695 WR=67.0 (p≈0 vs breakeven 54%)
- Conclusión: la demora ~300s del broker NO mata el edge; lo amplifica. Limitación (Charter Art. 10/13): medido en OTC, no spot. Validadción viva en spot pendiente antes de PROMOVER a REAL.

## DICTAMEN GLOBAL (decisión del director — R0)
**CICLO-001 = CONTINUAR**
- Motivo (Ruben, 2026-08-09): evidencia estadística suficiente para preservar la arquitectura; deuda crítica única era EXP-076 timing broker.
- Acción: cerrar EXCLUSIVAMENTE EXP-076 (hecho: medido en OTC 60s, WR 67-75%). No reformular la composición mientras esa deuda permaneciera abierta — ya cerrada.
- Estado tras cierre: arquitectura preservada; deuda de timing CERRADA (con salvedad de validación viva spot antes de PROMOVER a REAL).
- Siguiente frontera: validación en vivo en spot (demo REAL+OTC) antes de promover a producción.
