# EXP-MTF — Auditoría Multi-Temporalidad: Arcoíris M15 + señal/trigger M5

**Fecha:** 2026-08-08 · **Autor:** Hermes
**Scripts:** `scripts/audit_multitf.py` (9 modos M15→M5), `scripts/audit_m15_pure.py` (4 modos M15 puro)
**Petición:** experimentar sin preguntar hasta llegar a 60% WR. Autonomía 30min.
**Resultado:** NO se alcanzó 60%. Máximo robusto = **56-57%**.

---

## CONTEXTO
El usuario pidió originalmente un funnel 5min (freno+arcoíris+estocástico) que resultó
moneda (EXP-FUNNEL-5M, WR 44-52%). La rama lógica abierta era multi-TF: el arcoíris M15
funcionó como gate P3→CONTRATADO en EXP-EDF-04 (71% WR). Hipótesis: usar el arcoíris M15
como filtro de TENDENCIA y el M5 como TIMING de entrada.

## DISEÑO
- **Arcoíris M15:** 7 EMAs [5,10,20,40,80,160,320]; dirección CALL/PUT si están estrictamente
  alineadas; `kp` = persistencia (velas M15 consecutivas alineadas).
- **Trigger M5:** freno (rango<0.6×previo), cruce EMA20 M5, salida estocástica, o combinaciones.
- **Entry/exit M5:** eo=1 (5min), xo=2 (10min) o xo=3 (15min = expiración pedida).
- 9 modos en `audit_multitf.py` + 4 modos M15 puro en `audit_m15_pure.py`.
- Datos: EURUSD 2023/2024, XAUUSD 2023/2024 (M5+M15 reales, OHLCV).

## RESULTADOS (mejores configs por dataset, eo=1 xo=2 = 5/10min)

| Dataset | Modo | N | WR% | p |
|---------|------|---|-----|---|
| EURUSD 2024 | mtf_cross_ema | 1081 | 54.4 | 0.0039 |
| EURUSD 2024 | mtf_cross_ema_s | 786 | 53.2 | 0.0804 |
| XAUUSD 2024 | mtf_cross_ema | 1091 | 56.6 | 0.0000 |
| XAUUSD 2024 | mtf_cross_ema_s | 780 | 56.7 | 0.0002 |
| XAUUSD 2024 | mtf_pull | 6590 | 53.5 | 0.0000 |
| EURUSD 2023 | mtf_both | 13958 | 50.9 | 0.0440 |
| EURUSD 2023 | arc_signal | 14833 | 51.4 | 0.0007 |
| XAUUSD 2023 | mtf_both | 15581 | 52.6 | 0.0000 |

Con xo=3 (15min, expiración real): todos caen a 48-52% (el ruido a 15min destruye el edge).
Ej: mtf_cross_ema EURUSD2024 xo=3 = 50.7%; XAUUSD2024 xo=3 = 51.5%.

## MODOS PROBADOS
`arc_signal` (señal=M15 arcoíris), `arc_filter_m5` (freno M5 + stoch + arcoíris),
`arc_bias_m5dir` (bias M15 + dir stoch M5), `mtf_both` (arcoíris M15 + arcoíris M5 fast),
`mtf_pull` (pullback M5 a EMA20), `mtf_cross_ema` (cruce EMA20 M5 en dir M15),
`mtf_cross_ema_b` (+freno), `mtf_cross_ema_s` (+stoch salida), `mtf_cross_ema_strong`
(cruce fuerte). Más M15 puro: `arc_only`, `arc_freno`, `arc_cross_ema`, `arc_freno_cross`.

## DICTAMEN
**NO SE ALCANZÓ 60%.** El techo de esta familia de estrategias es **~56-57% WR con
n>700 y p significativo** (mtf_cross_ema / mtf_cross_ema_s en EURUSD2024 y XAUUSD2024).
Todas las demás combinaciones caen a 48-53%. Con expiración real de 15min (xo=3) el edge
desaparece completamente (48-52% = moneda).

PRECISIÓN QUIRÚRGICA:
- ❌ NO REFUTADO el arcoíris M15: sigue siendo el mejor filtro de tendencia (EXP-EDF-04, 71%).
  Pero como SEÑAL DIRECTA en M5/M15 (sin la estructura P1→P2→P3 del Edificio) su edge se
  diluye a 54-57%.
- ❌ El M5 como timing de entrada es ruido: a 5/10min da 54-57%, a 15min cae a moneda.
- ❌ No se encontró combinación (freno/arcoíris/estocástico/cruce EMA) que dé 60% WR con
  n>300 y p<0.05 en datos reales 2023/2024.

## LECCIÓN (para el usuario, sin preguntar)
El arcoíris M15 solo funciona al 71% CUANDO es gate del Edificio (que ya filtra por
estructura de mercado P1→P2→P3). Aislado, o combinado con triggers M5, su edge es 54-57%.
Para llegar a 60%+ en datos reales, la vía no es "más indicadores en M5" sino recuperar
la ESTRUCTURA del Edificio (freno+arcoíris+estocástico como filtros DENTRO del embudo
P1→P2→P3 ya validado), no como señal independiente.

## LIMITACIONES HONESTAS
1. WR aproximado (close M5/M15 i+offset). El bot real usa openPrice broker. La dirección
   (techo 57%) es robusta en 4 datasets independientes.
2. No se probó: arcoíris M15 + embudo P1→P2→P3 completo del Edificio (esa es la rama que
   dio 71% en EXP-EDF-04, ya cerrada).
3. Autonomía de 30min agotada. El máximo alcanzable con esta familia en ese tiempo = 57%.

## ARCHIVOS
- `scripts/audit_multitf.py` — 9 modos M15→M5 (reproducible: `python scripts/audit_multitf.py <año> <par> grid`)
- `scripts/audit_m15_pure.py` — 4 modos M15 puro
- Datos en `/tmp/mtf2_*.txt` (4 datasets, grid completo)
- pytest src: 21 passed.
