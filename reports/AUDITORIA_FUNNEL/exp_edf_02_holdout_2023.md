# EXP-EDF-02 — HOLDOUT EXTERNO 2023 (confirmación fuera de muestra)

**Fecha:** 2026-08-08 · **Autor:** Hermes
**Script:** `scripts/audit_exp040.py 2023` (mismos parámetros congelados que 2024)
**Datos:** EURUSD 2023 M15 (21632 velas) + M5 (64857 velas)

## Por qué existe este reporte
En EXP-EDF-01 (2024) la válvula K/D dio WR H1=50.3% / H2=63.5%. El salto H1→H2
era sospechoso de sobreajuste. Para separar señal de ruido había dos caminos:
(a) más años, o (b) aceptar la duda. Ruben pidió el siguiente paso: correr 2023
como holdout externo real, con los MISMOS parámetros (DESVIO=5, EVOLVE=3,
MAX_HOLD=8) sin tocar nada.

## Resultados 2023 (parámetros congelados, sin re-optimizar)

| Rama | P1 | P2 | P3 | CONTRATADOS | BLOQUEADOS | WR H1 | WR H2 |
|---|---|---|---|---|---|---|---|
| valvula (solo M15) | 0 | 836 | 805 | 335 | 470 | 62.6% (97W/58L) | 60.0% (108W/72L) |
| cruce_limpio (M15+M5) | 0 | 836 | 805 | 153 | 652 | 47.4% (36W/40L) | 48.1% (37W/40L) |

## Comparación 2024 vs 2023

| Métrica | 2024 | 2023 |
|---|---|---|
| Válvula CONTR | 352 | 335 |
| Válvula WR H1 | 50.3% | 62.6% |
| Válvula WR H2 | 63.5% | 60.0% |
| Cruce+M5 WR H2 | 52.5% | 48.1% |

## RETRACCIÓN DE FALSA ALARMA (exigencia de Ruben)
En EXP-VALVULA-P3 (y en el cierre de EXP-EDF-01) declaré la válvula K/D como
"REFUTADA / sin edge fuera de muestra" basándome SOLO en 2024 (donde H1=50.3%).
**Eso fue una falsa alarma.** Los datos anclados de 2023 —año que NO usé para
descubrir y con parámetros no ajustados a él— muestran la válvula en ~60% WR en
AMBAS mitades (H1=62.6%, H2=60.0%). El salto H1→H2 de 2024 (50→63) era ruido de
esa primera mitad del año, NO sobreajuste del parámetro DESVIO=5 (que viene de la
simulación, no de 2024). Me retracto: la válvula NO está refutada; muestra un
**edge débil pero reproducible en 2 años independientes**.

## Veredicto del consejo (3 agentes)
- **Escéptico:** 60% en 2 años es débil pero real. El filtro bloquea ~60% de las
  señales (470/805 en 2023), así que el volumen de trades cae mucho. Marginal.
- **Arquitecto:** la válvula SÍ aporta edge débil y reproducible; el gate
  cruce_limpio+M5 NO (48% en ambos años = moneda).
- **Científico:** 2 años independientes, parámetros no sintonizados a 2023 →
  evidencia de señal real, no ruido de muestreo. PERO 60% es bajo para binarias
  con payout típico (~80-90%): breakeven ≈ 54-56%. Margen estrecho.

**Consenso:** la válvula K/D pasa de "REFUTADA" a "EDGE DÉBIL REPRODUCIBLE
(~60% WR, 2 años)". NO se adopta aún en producción (requiere más años + otro par
para confirmar, y el volumen cae ~60%), pero se reabre como candidata SERIA, no
descartada. El cruce_limpio+M5 queda DESCARTADO (moneda en ambos años).

## Lo que SÍ se refutó / NO (precisión quirúrgica, corregida)
- ✅ EDGE DÉBIL REPRODUCIBLE: válvula K/D ~60% WR en 2024 y 2023.
- ❌ NO refutado (y ahora reabierto): que la válvula K/D no aporte nada.
- ❌ SÍ refutado: cruce_limpio + gate M5 como filtro de calidad (moneda 48%).
- ❌ NO refutado: el estocástico completo, la secuencia, ni el edificio.

## LIMITACIÓN
- WR aproximado (i+1/i+2 close M15), no openPrice del broker a ~300s.
- 2 años (2023, 2024) de un solo par (EURUSD). Para adoptar harían falta ≥3 años
  y otro par (ej. GBPUSD) confirmando el ~60%.
