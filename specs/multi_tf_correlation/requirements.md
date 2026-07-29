# Requirements — multi_tf_correlation

> **Feature ID:** 19
> **Status:** spec_ready
> **Depends on:** None (H1 data already prefetched)

---

## R1 — Multi-TF Trend Detection

CUANDO el scanner evalúa un candidato STRAT-F,
EL sistema DEBE calcular la tendencia actual de cada timeframe (M1, M5, M15, H1)
usando regresión lineal simple (pendiente de precio sobre últimas N velas).

---

## R2 — Confluence Score

CUANDO se calculan las tendencias de 4 timeframes,
EL sistema DEBE calcular un `confluence_score`:
- 4/4 alineados (todos CALL o todos PUT): +0.15
- 3/4 alineados: +0.05
- 2/4 o menos: -0.05 (penalización por conflicto)

---

## R3 — Trend Calculation Method

Para cada timeframe, el sistema DEBE:
1. Tomar las últimas N velas (M1: 10, M5: 8, M15: 6, H1: 4)
2. Calcular regresión lineal sobre cierres
3. Si pendiente > +threshold → tendencia CALL
4. Si pendiente < -threshold → tendencia PUT
5. Si pendiente entre -threshold y +threshold → neutro (no cuenta)

Threshold por defecto: 0.001 (configurable).

---

## R4 — Confluence Integration

CUANDO se calcula el score final de un candidato,
EL sistema DEBE sumar `confluence_bonus` al score:
`final_score = base_score + confluence_bonus`

---

## R5 — Confluence Logging

CUANDO se calcula confluence,
EL sistema DEBE loggear:
`[CONFLUENCE] ASSET: M1=CALL M5=CALL M15=CALL H1=NEUTRAL → 3/4 +0.05`

---

## R6 — H1 Data Availability

SI los datos H1 no están disponibles para un activo,
EL sistema DEBE usar solo M1/M5/M15 para el cálculo de confluence
y ajustar los bonuses proporcionalmente:
- 3/3 alineados: +0.10
- 2/3 alineados: +0.03
- 1/3 o menos: -0.03

---

## R7 — Configuration

EL sistema DEBE exponer以下 parámetros en `config.py`:
- `CONFLUENCE_ENABLED = True`
- `CONFLUENCE_BONUS_4OF4 = 0.15`
- `CONFLUENCE_BONUS_3OF4 = 0.05`
- `CONFLUENCE_PENALTY_LOW = -0.05`
- `CONFLUENCE_TREND_THRESHOLD = 0.001`

---

## R8 — Tests

Los tests DEBEN cubrir:
- 4/4 alineados → bonus máximo
- 3/4 alineados → bonus medio
- 2/4 o menos → penalización
- H1 no disponible → fallback a 3 timeframes
- Neutro en un TF → no cuenta como alineado
- Threshold configurable
- Integración con scanner (mock candles)
