# EXP-084 — Redes neuronales tabulares sobre SPOT M15 REAL

**Dominio:** SPOT M15 REAL — EURUSD_M15 (543.310 velas, 2004-2025) + XAUUSD_M15 (346.568 velas, 2012-2026)
**Muestra utilizable:** 889.214 filas · **Features:** 28 · **POI rate:** 21,46% de las velas
**Modelos:** LightGBM + MLP sklearn (128,64) · **Split temporal estricto 70/15/15, sin shuffle**
**Timing:** señal en cierre vela i → entry `open[i+1]`, exit `close[i+2]`; label CALL-gana
**Breakeven:** 54% (payout 85%) · **Umbral decisión:** 0.55 · runtime 201 s

| Split | Rango | n | base rate CALL |
|---|---|---|---|
| train | 2004-01-07 → 2020-09-17 | 622.449 | 48,96% |
| val | 2020-09-17 → 2023-07-09 | 133.382 | 49,71% |
| test | 2023-07-09 → 2026-07-24 | 133.383 | 50,87% |

Cierra la deuda R9 del CICLO-002: la válvula K/D no abría ninguna señal en M15 real (n=0).
Aquí se relaja a feature continua (`kd_sep`, `kd_slope1/3`) y se añade **POI explícito**
(`in_poi`, causal vía `swing_levels_causal` + `in_poi_band` de `exp_common.py`), que era
lo que faltaba en las NN del CICLO-001 (EXP-NN-1/2).

---

## 1. LightGBM — WR por decil de confianza

| Conjunto | Selección | ops | wins | WR | p vs 54% |
|---|---|---|---|---|---|
| VAL | todas | 133.382 | 69.173 | 51,9% | 1,000 |
| VAL | top50% | 66.691 | 35.489 | 53,2% | 1,000 |
| VAL | top25% | 33.345 | 18.251 | **54,7%** | **0,0036** |
| VAL | top10% | 13.338 | 7.521 | **56,4%** | **1,7e-08** |
| VAL | top05% | 6.669 | 3.847 | **57,7%** | **8,4e-10** |
| VAL | umbral 0,55 | 10.912 | 6.177 | **56,6%** | **2,4e-08** |
| **TEST** | todas | 133.383 | 67.868 | 50,9% | 1,000 |
| **TEST** | top50% | 66.691 | 34.526 | 51,8% | 1,000 |
| **TEST** | top25% | 33.345 | 17.503 | 52,5% | 1,000 |
| **TEST** | top10% | 13.338 | 7.146 | 53,6% | 0,839 |
| **TEST** | top05% | 6.669 | 3.617 | 54,2% | 0,354 |
| **TEST** | umbral 0,55 | 11.610 | 6.229 | 53,7% | 0,777 |

**AUC:** val 0,5287 · **test 0,5206**.
El lift significativo de VAL **NO sobrevive** al TEST out-of-sample → sobreajuste al régimen 2020-2023.

### Por activo (TEST, LightGBM)
| Activo | todas | top25% | top10% |
|---|---|---|---|
| EURUSD (n=61.375) | 51,2% (p=1,0) | 53,2% (p=0,97) | 54,2% (p=0,355) |
| XAUUSD (n=72.008) | 50,6% (p=1,0) | 51,9% (p=1,0) | 52,4% (p=0,997) |

## 2. MLP (sklearn)

AUC val 0,5272 · **test 0,5180**.

| Conjunto | todas | top25% | top10% | top05% | umbral 0,55 |
|---|---|---|---|---|---|
| VAL | 51,8% | 53,9% (p=0,61) | 54,7% (p=0,059) | 55,5% (p=0,009) | 53,5% (n=44.249) |
| TEST | 50,7% | 51,9% (p=1,0) | 52,9% (p=0,995) | 53,4% (p=0,830) | 51,6% (n=44.677, p=1,0) |

Consistente con LightGBM: sin edge en TEST.

## 3. Diagnóstico POI (TEST, LightGBM) — el punto clave del encargo

| Zona | ops | WR global | top25% | top10% | top05% | umbral 0,55 |
|---|---|---|---|---|---|---|
| **EN POI** | 20.982 | 51,8% (p≈1,0) | 53,7% (p=0,659) | 55,2% (p=0,131) | 55,8% (p=0,132) | 55,3% (n=2.052, p=0,121) |
| **FUERA POI** | 112.401 | 50,7% (p=1,0) | — | — | — | — |

Gap EN_POI vs FUERA_POI ≈ **1,1 pp**. En OTC 60s el CICLO-001 medía 71-84% dentro de POI
vs 47% fuera (gap ~25 pp). **En M15 REAL el efecto POI prácticamente desaparece.**
La dirección del efecto es la esperada (POI mejora), pero la magnitud no llega a
significancia (p≥0,12) y el top10% en POI (55,2%) apenas roza el breakeven.

### Ablación: LightGBM SIN la feature `in_poi`
AUC test **0,5206 (idéntico)** · top10% 53,2% (p=0,96) · top05% 54,2% (p=0,37).
Quitar POI no degrada el modelo → **la red no está usando POI para predecir**.

## 4. Feature importances (LightGBM, split-count, 28 features)

Top 20:
```
hour        349   range_atr  248   atr_ratio 248   ret1        225
dist_ema160 219   dist_ema5  217   dist_ema80 187  lower_wick  182
dist_ema10  180   k          159   dist_ema20 148  ret20       148
dist_ema40  143   dist_ema320 139  upper_wick 139  k_slope1    129
body_ratio  124   ema_spread 114   ret5      104   kd_sep       95
```
Cola (herramientas del Edificio): `kd_slope1`=94 · `in_poi`=**87** · `arcoiris_stack`=**6** ·
`k_extremo_lo`=**0** · `k_extremo_hi`=**0**.

**Lectura:**
- **Arcoíris:** las *distancias* a las EMAs sí se usan (dist_ema5/80/160 en el top), pero el
  **apilamiento estricto** (la regla real del gate, `arcoiris_stack`) tiene importancia ≈0.
  La red aprovecha la EMA como medida de desviación, no la regla binaria del Edificio.
- **Válvula K/D:** `k`=159 y `k_slope1`=129 aportan algo; `kd_sep`/`kd_slope1` (~95) son
  medios-bajos; los **extremos 20/80 valen exactamente 0**. La válvula tal como está
  formulada no aporta información en M15 real.
- **POI:** importancia baja (87) y ablación neutra → no aporta señal utilizable aquí.
- Lo que más pesa (`hour`, `range_atr`, `atr_ratio`, `ret1`) es estacionalidad y
  microestructura/volatilidad, y aun así no genera WR significativo en TEST.

## 5. Veredicto honesto

**NO. La red no aprende un edge explotable en SPOT M15 REAL con nuestras herramientas.**

1. AUC test 0,52 (casi azar) en ambos modelos. Ningún decil de TEST supera el breakeven
   con significancia: el mejor es top05% = 54,2% con **p=0,354**. Sin ventaja demostrada.
2. El lift de VAL (top05% 57,7%, p=8e-10) es real *en validación* pero **se evapora en TEST**:
   evidencia clara de deriva de régimen / sobreajuste, no de edge estructural.
3. El hallazgo gate×POI del CICLO-001 (71-84% en OTC 60s) **no se transporta a M15 real**:
   gap de 1,1 pp, no significativo, y la ablación sin POI da resultados idénticos.
4. Las tres herramientas del Edificio salen mal paradas en importancias: apilamiento del
   arcoíris ≈0, extremos estocásticos =0, POI bajo e inútil en ablación. Solo sobreviven
   como señales débiles las *distancias* EMA y la pendiente de K.

Esto **no falsa** el edge en OTC 60s (dominio distinto, EXP-076/077 siguen vigentes). Lo que
establece, con 133k operaciones de test, es que la composición actual **no es transportable
a SPOT M15 REAL**. Es una conclusión más fuerte que la de CICLO-002 (que era "n=0 por
insuficiencia de disparos"): aquí hay muestra masiva y el resultado es **negativo con evidencia**.

**Implicación:** promover el gate del Edificio a mercado REAL requiere rediseñar la señal
para M15 (o aceptar que el edge es específico del dominio OTC). Añadir capacidad de modelo
(LSTM/torch) no está justificado: el tabular no muestra lift, que era el gate de la spec
EXP-EDIFICIO-NN-SCORE.

## 6. Reproducibilidad y archivos
- `exp084_nn_spot_m15.py` — script único (semilla 42). Reutiliza `reports/CICLO-001/exp_common.py`
  (POI causal, `wr_stats`/`binomial_p`). Estocástico y EMAs vectorizados: equivalencia
  numérica verificada contra `compute_stoch_full` (máx. desviación 9,9e-14).
- `_raw_results.json` — todos los números crudos de este reporte.
- No se modificó `exp_common.py` ni `edificio_contratacion.py`.
