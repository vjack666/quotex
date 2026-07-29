# Requirements — kelly_criterion_sizing (Enhanced)

> **Feature ID:** 20
> **Status:** spec_ready
> **Depends on:** Feature 18 (LightGBM Scorer)
> **Replaces:** Basic Kelly (Feature 13, already done)

---

## R1 — Rolling Win Rate

CUANDO se calcula Kelly,
EL sistema DEBE usar rolling win rate de las últimas 50 operaciones
(en vez de todo el histórico), para adaptarse a cambios recientes en performance.

---

## R2 — Per-Strategy Win Rate

CUANDO se calcula Kelly,
EL sistema DEBE calcular win rate filtrando por `strategy_origin` si se especifica.
Por defecto usa win rate global de STRAT-F.

---

## R3 — Confidence-Weighted Sizing

SI LightGBM (Feature 18) está disponible,
EL sistema DEBE ajustar el fraction según la confidence del modelo:
- confidence > 0.7: fraction × 1.2 (mayor apuesta en señales seguras)
- confidence 0.4-0.7: fraction × 1.0 (normal)
- confidence < 0.4: fraction × 0.5 (reducir en señales débiles)

---

## R4 — Half-Kelly Default

EL factor de Kelly fraccional DEBE usar half-Kelly (0.5x) por defecto.
Configurable via `KELLY_FRACTION = 0.5` en config.py.

---

## R5 — Dynamic Fraction by Edge

CUANDO el edge (win_rate × avg_payout - (1-win_rate)) es:
- > 0.2: fraction = 0.5 (half-Kelly)
- 0.1 - 0.2: fraction = 0.3 (conservative)
- < 0.1: fraction = 0.1 (minimal)
- ≤ 0: fraction = 0.0 (no operar)

---

## R6 — Stake Limits

EL stake resultante DEBE respetar:
- Mínimo: $1.00 (nunca menos)
- Máximo: 5% del balance actual (nunca más)
- Si Kelly calculado excede máximo, usar máximo.

---

## R7 — Logging

CUANDO se calcula Kelly,
EL sistema DEBE loggear:
`[KELLY] WR=60.0% payout=90% edge=0.14 → fraction=0.35 stake=$3.15`

---

## R8 — Fallback to Basic Kelly

SI LightGBM no está disponible,
EL sistema DEBE usar la fórmula básica Kelly (Feature 13 original)
sin confidence weighting.

---

## R9 — Integration with Massaniello

CUANDO se calcula el stake final con Kelly,
EL sistema DEBE:
1. Calcular stake = balance × kelly_fraction
2. Si stake < initial_amount (config), usar initial_amount
3. Si stake > max_stake (5% balance), usar max_stake
4. Pasar stake como `initial_amount` al MassanielloRiskManager

---

## R10 — Tests

Los tests DEBEN cubrir:
- Rolling win rate (últimas 50 vs total)
- Per-strategy filtering
- Confidence weighting (mock LightGBM)
- Edge cases: 100% WR, 0% WR, insufficient data
- Stake limits (min, max)
- Fallback sin LightGBM
- Integración con Massaniello (mock)
