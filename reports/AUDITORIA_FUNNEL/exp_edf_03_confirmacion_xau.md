# EXP-EDF-03 — Confirmación externa de la válvula K/D (holdout de par y año)

**Fecha:** 2026-08-08 · **Autor:** Hermes
**Script:** `scripts/audit_exp040.py <año> <instrumento>` (parámetros congelados: DESVIO=5, EVOLVE=3, MAX_HOLD=8)
**Motivo:** EXP-EDF-01 midió la válvula del motor real en EURUSD 2024 (WR H2=63.5%) y su
holdout 2023 (WR H2=60.0%). Para confirmar que es señal real (no ruido de EURUSD),
necesitaba un TEST DE GENERALIZACIÓN: otro par (XAUUSD) y/o otro año. EURUSD solo
tiene 2023/2024; XAUUSD tiene 2023/2024/2025. Se elige XAUUSD 2024 (par distinto,
mismos params).

## Resultados (parámetros NO re-optimizados, venían de la sim de la máquina B)

| Instrumento | Año | P3 | CONTR | WR H1 | WR H2 |
|---|---|---:|---:|---:|---:|
| EURUSD | 2024 | 855 | 352 | 50.3% | **63.5%** |
| EURUSD | 2023 | 805 | 335 | 62.6% | **60.0%** |
| XAUUSD | 2024 | 748 | 302 | 51.1% | **57.7%** |
| — cruce_limpio+M5 EURUSD 2024 | | 855 | 170 | 38.9% | **52.5%** |
| — cruce_limpio+M5 EURUSD 2023 | | 805 | 153 | 47.4% | **48.1%** |
| — cruce_limpio+M5 XAUUSD 2024 | | 748 | 131 | 43.9% | **45.9%** |

## Interpretación
- **Válvula K/D:** edge débil pero REPRODUCIBLE en 2 pares × años distintos.
  WR H2 ∈ [57.7%, 63.5%]. El filtro bloquea ~60% de señales P3 (446/748 en XAUUSD).
- **cruce_limpio + gate M5:** moneda en TODO (45-52%). DESCARTADO como filtro de calidad.
- La válvula usa stoch 14,3,3 + DESVIO=5 calibrados en EURUSD. Que funcione en XAUUSD
  (oro, comportamiento de rango/distinto) apunta a señal estructural, no overfitting a EURUSD.

## Retractación actualizada (de EXP-VALVULA-P3)
La declaración original "válvula REFUTADA / sin edge" fue falsa alarma (basada en 1 año
y en una definición distinta de válvula). Con 2 pares × años la válvula del motor real
muestra **edge débil reproducible (~58-63% WR H2)**. Pasa a EDGE DÉBIL CONFIRMADO
(externalizado), no adoptada aún en REAL.

## Veredicto del consejo
- **Escéptico:** 58-63% en 3 datasets independientes es real, pero marginal. El filtro
  mata 60% del volumen. Para binarias con payout 80-90% el breakeven es 54-56%: el margen
  es estrecho pero positivo.
- **Arquitecto:** la válvula SÍ aporta edge débil y generalizable; el gate M5 NO.
- **Científico:** 3 datos OOS independientes (2 pares) → evidencia de señal, no ruido.
  PERO: sample chico (3 años-par), y el WR es aproximado (i+1/i+2 close M15).

**Consenso:** válvula = EDGE DÉBIL CONFIRMADO (externalizado a otro par). NO se adopta en
REAL sin: (a) ≥3 años de EURUSD + GBPUSD/otro par adicional, (b) validar el WR con el
openPrice real del broker (no aproximación i+1/i+2), (c) medir el impacto de perder 60%
de volumen en el ciclo Massaniello.

## Lo que SÍ / NO se refutó (precisión quirúrgica)
- ✅ EDGE DÉBIL CONFIRMADO: válvula K/D ~58-63% WR H2 en EURUSD(2023,2024)+XAUUSD(2024).
- ❌ DESCARTADO: cruce_limpio + gate M5 (moneda en todos los datasets).
- ❌ NO refutado: el estocástico completo, la secuencia, ni el edificio.
- ❌ NO refutado (reabierto): que la válvula aporte edge — AHORA SÍ confirmado débil.

## LIMITACIÓN
- WR aproximado (i+1/i+2 close M15), no openPrice del broker a ~300s.
- Sample chico: 2 pares × años. Para adoptar en REAL: más años + otro par + WR con broker.
- XAUUSD es más volátil; el DESVIO=5 está calibrado en EURUSD. Que funcione sugiere
  robustez, pero un re-calibre por par podría mejorar (fuera del alcance de EXP-EDF-03).
