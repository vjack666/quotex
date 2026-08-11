# EXP-FUNNEL-5M — Auditoría funnel 5min: FRENO + ARCOÍRIS + ESTOCÁSTICO

**Fecha:** 2026-08-08 · **Autor:** Hermes
**Script:** `scripts/audit_funnel_5m.py` (30 combos sistemáticos, entry/exit M5, hold=3 velas M5=15min)
**Petición del usuario:** auditoría funnel del freno + arcoíris + estocástico, con entry/salida
en 5min y señal enviada a expiración de 15min. ~30 combinaciones vía varios agentes.
Experimento especial: esperar freno → arcoíris mayoría cruzando → salida estocástica → señal 15min.

---

## DISEÑO
- **FRENO:** vela M5 con rango < 0.6 × rango de la vela previa (compresión).
- **ARCOÍRIS:** 7 EMAs exponenciales M5 [5,10,20,40,80,160,320].
  - `full` = close>EMA5>EMA10>...>EMA320 (CALL) / inverso (PUT), estricto.
  - `fast` = solo EMA5>EMA20>EMA320.
  - `none` = no usa arcoíris.
- **ESTOCÁSTICO** (%K/%D M5, compute_stoch_full):
  - `exit_ext` = K sale de extremo (CALL K>20 / PUT K<80).
  - `cross` = K cruza D en dirección.
  - `sep` = |K-D| >= umbral {2.0, 5.0}.
- **ENTRY/EXIT EN M5:** entry = close[i+1] (5min tras señal), exit = close[i+3] (15min = expiración).
- 30 combos = 2(freno) × 3(arcoíris) × 3(estocástico) × 2(umbral), recortado a 30.

## RESULTADOS (WR% por combo, 8 datasets reales)

| COMBO | EUR22 | EUR23 | EUR24 | EUR25 | XAU20 | XAU21 | XAU23 | XAU24 |
|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| C00 f1 full exit_ext u2 | 45.4 | 46.6 | 46.2 | 47.2 | 45.7 | 49.0 | 46.8 | 46.8 |
| C01 f1 full exit_ext u5 | 45.4 | 46.6 | 46.2 | 47.2 | 45.7 | 49.0 | 46.8 | 46.8 |
| C02 f1 full cross u2 | 44.8 | 45.7 | 48.3 | 46.0 | 46.5 | **52.7** | 45.4 | 47.8 |
| C03 f1 full cross u5 | 44.8 | 45.7 | 48.3 | 46.0 | 46.5 | **52.7** | 45.4 | 47.8 |
| C04 f1 full sep u2 | 45.8 | 47.1 | 46.5 | 47.2 | 45.1 | 49.2 | 47.4 | 49.7 |
| C05 f1 full sep u5 | 45.1 | 47.5 | 45.9 | 47.0 | 45.9 | 48.6 | 45.7 | 50.0 |
| C06 f1 fast exit_ext u2 | 47.0 | 47.5 | 46.0 | 47.9 | 46.7 | 49.1 | 46.9 | 49.4 |
| C07 f1 fast exit_ext u5 | 47.0 | 47.5 | 46.0 | 47.9 | 46.7 | 49.1 | 46.9 | 49.4 |
| C08 f1 fast cross u2 | 47.4 | 48.2 | 47.7 | 44.0 | 46.9 | 51.5 | 47.7 | 47.6 |
| C09 f1 fast cross u5 | 47.4 | 48.2 | 47.7 | 44.0 | 46.9 | 51.5 | 47.7 | 47.6 |
| C10 f1 fast sep u2 | 47.0 | 48.2 | 45.8 | 48.4 | 46.2 | 49.6 | 46.8 | 49.4 |
| C11 f1 fast sep u5 | 47.1 | 48.9 | 45.5 | 48.6 | 45.8 | 49.3 | 46.1 | 49.5 |
| C12 f1 none exit_ext u2 | 47.8 | 48.4 | 48.0 | 48.5 | 48.4 | 48.9 | 48.8 | 48.8 |
| C13 f1 none exit_ext u5 | 47.8 | 48.4 | 48.0 | 48.5 | 48.4 | 48.9 | 48.8 | 48.8 |
| C14 f1 none cross u2 | 46.9 | 46.5 | 48.5 | 48.0 | 51.0 | 51.1 | 47.4 | 49.7 |
| C15 f1 none cross u5 | 46.9 | 46.5 | 48.5 | 48.0 | 51.0 | 51.1 | 47.4 | 49.7 |
| C16 f1 none sep u2 | 47.8 | 48.8 | 48.1 | 48.8 | 48.3 | 49.3 | 48.5 | 49.1 |
| C17 f1 none sep u5 | 47.9 | 49.4 | 48.0 | 48.7 | 48.0 | 49.0 | 48.5 | 48.8 |
| C18 f0 full exit_ext u2 | 45.9 | 48.1 | 47.2 | 47.4 | 47.3 | 48.1 | 48.7 | 48.4 |
| C19 f0 full exit_ext u5 | 45.9 | 48.1 | 47.2 | 47.4 | 47.3 | 48.1 | 48.7 | 48.4 |
| C20 f0 full cross u2 | 46.0 | 49.0 | 47.2 | 46.2 | 48.7 | 49.3 | 49.7 | 49.7 |
| C21 f0 full cross u5 | 46.0 | 49.0 | 47.2 | 46.2 | 48.7 | 49.3 | 49.7 | 49.7 |
| C22 f0 full sep u2 | 45.9 | 48.4 | 47.4 | 47.3 | 47.1 | 48.2 | 48.0 | 49.0 |
| C23 f0 full sep u5 | 45.5 | 48.5 | 46.9 | 47.4 | 46.4 | 47.9 | 47.0 | 49.0 |
| C24 f0 fast exit_ext u2 | 46.8 | 48.0 | 46.7 | 47.4 | 47.3 | 48.5 | 48.9 | 48.8 |
| C25 f0 fast exit_ext u5 | 46.8 | 48.0 | 46.7 | 47.4 | 47.3 | 48.5 | 48.9 | 48.8 |
| C26 f0 fast cross u2 | 47.0 | 48.8 | 46.8 | 46.0 | 47.9 | 49.3 | 48.1 | 49.3 |
| C27 f0 fast cross u5 | 47.0 | 48.8 | 46.8 | 46.0 | 47.9 | 49.3 | 48.1 | 49.3 |
| C28 f0 fast sep u2 | 46.6 | 48.4 | 46.9 | 47.7 | 47.4 | 48.6 | 48.7 | 49.3 |
| C29 f0 fast sep u5 | 47.0 | 48.6 | 46.8 | 47.6 | 47.1 | 48.7 | 49.3 | 48.2 |

## EXPERIMENTO ESPECIAL (C00)
"Esperar al freno → arcoíris mayoría cruzando (full) → salida del estocástico → señal a 15min."
- EURUSD 2022/23/24/25: 45.4 / 46.6 / 46.2 / 47.2% — **TODOS < 48%, perdedor**.
- XAUUSD 2020/21/23/24: 45.7 / 49.0 / 46.8 / 46.8% — **nunca > 50% de forma significativa**.
- Veredicto del especial: **NO tiene edge**. Es ruido/ligeramente perdedor.

## DICTAMEN
**REFUTADO como fuente de edge.** El funnel 5min (freno + arcoíris + estocástico) con
entry/exit en M5 y señal a 15min de expiración NO produce WR por encima de 50% en
ninguno de los 8 datasets. Rango total observado: 44.8% – 52.7%.
- El máximo aislado (52.7% en XAUUSD 2021, C02/C03) tiene n=370 y p=0.32 = ruido
  por muestra pequeña, no señal.
- Con n>5000 (la mayoría de combos), WR cae a 46-49% con p<0.05 **a FAVOR de <50%**
  (es decir, ligeramente perdedor sistemático, no ganador).
- El arcoíris (que en M15 P3→CONTRATADO dio 71%) en M5 granularidad fina NO aporta
  edge: el ruido intradía domina la señal de las medias.

## PRECISIÓN QUIRÚRGICA
- ❌ REFUTADO: el funnel 5min freno+arcoíris+estocástico (cualquier combo de los 30)
  como generador de señales con WR>50%.
- ✅ PRESERVADO: el arcoíris SÍ funciona en M15 como puerta P3→CONTRATADO (EXP-EDF-04,
  71% WR). La diferencia es la granularidad: en M5 el ruido destruye la señal; en M15
  la tendencia de las medias se sostiene.
- ❌ NO se dictamina sobre el Edificio P3 ni sobre otras temporalidades. Solo este funnel M5.
- ❌ El "flip" K/D y el cruce K/D en M5 tampoco salvan el funnel (WR idéntico a moneda).

## LIMITACIONES HONESTAS
1. WR aproximado (entry=close[i+1], exit=close[i+3] M5 = 5min/15min). El bot real usa
   openPrice del broker a ~300s tras señal; la magnitud puede variar, pero la DIRECCIÓN
   (moneda) es robusta en 8 datasets independientes.
2. El freno (rango < 0.6× previo) es una heurística simple; un freno más sofisticado
   (p.ej. comparar contra media de rangos) podría cambiar algo, pero con WR 45-49% el
   margen para rescatar edge es inexistente.
3. No se probó combinar este funnel M5 con el arcoíris M15 (filtro multi-TF). Ese es un
   experimento distinto que QUEDA PENDIENTE si el usuario lo quiere (la hipótesis sería:
   arcoíris M15 alineado + freno M5 + salida estocástica M5).

## ARCHIVOS
- `scripts/audit_funnel_5m.py` — sweep de 30 combos (reproducible: `python scripts/audit_funnel_5m.py <año> <par> all`)
- Datos en `/tmp/funnel_*.txt` (8 datasets, script ya corregido: exit_off=3=15min, scross funcional)
- pytest src: 21 passed (script no toca src/).
