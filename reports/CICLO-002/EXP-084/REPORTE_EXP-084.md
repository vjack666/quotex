# EXP-084 — Redes neuronales sobre SPOT M15 REAL (aprendizaje de herramientas)

**Fecha:** 2026-08-10
**Dominio:** SPOT M15 REAL — EURUSD_M15 (543k velas, 2004-2025) + XAUUSD_M15 (346k velas, 2012-2025)
**Muestra total:** 889.214 velas · **Features:** 28 (arcoíris, válvula K/D relajada, POI, stoch, wicks, ATR, retornos, hora/día)
**Modelos:** LightGBM (tabular) + MLP sklearn · **Split:** temporal estricto 70/15/15 (SIN shuffle)
**Target:** CALL gana a +900s (timing broker aproximado M15: entry open[i+1], exit close[i+2])
**Breakeven:** 54% (payout 85%) · **Umbral decisión:** 0.55

---

## Contexto (por qué este experimento)

El usuario pidió usar redes neuronales para aprender el comportamiento del mercado
y ver cómo NUESTRAS HERRAMIENTAS (arcoíris, válvula K/D, POI) ayudan, sobre SPOT
(real), no OTC. Esto cierra la deuda R9 de CICLO-002 (la válvula K/D no abría en M15
real, n=0). El CICLO-001 había hallado que gate×POI en OTC 60s daba WR 71-84% dentro
de POI (p≤0.0025) — pero las NN de aquel ciclo NO incluyeron POI como feature. Este
EXP-084 SÍ incluye POI explícito, para testear si ese edge sobrevive a M15 REAL.

## Resultados — LightGBM (modelo principal)

| Conjunto | Métrica | ops | WR | p vs 54% |
|----------|---------|-----|-----|----------|
| TEST global | todas | 133.383 | 50.9% | 1.000 |
| TEST | top50% conf | 66.691 | 51.8% | 1.000 |
| TEST | top25% conf | 33.345 | 52.5% | 1.000 |
| TEST | top10% conf | 13.338 | 53.6% | 0.839 |
| TEST | top05% conf | 6.669 | 54.2% | 0.354 |
| TEST | umbral 0.55 | 11.610 | 53.7% | 0.777 |
| VAL global | top10% conf | 13.338 | 56.4% | **1.7e-08** |
| VAL | top05% conf | 6.669 | 57.7% | **8.4e-10** |

**AUC:** train implícito · val 0.5287 · **test 0.5206** (≈azar; 0.50 = sin señal).

### Por activo (TEST)
- EURUSD: global 51.2% (p=1.0), top10 54.2% (p=0.35)
- XAUUSD: global 50.6% (p=1.0), top10 52.4% (p=0.997)

### DENTRO vs FUERA de POI (TEST, LightGBM) — el hallazgo crítico
| Zona | ops | WR global | top10 WR | top05 WR |
|------|-----|-----------|----------|----------|
| **EN POI** | 20.982 | 51.8% (p≈1.0) | 55.2% (p=0.13) | 55.8% (p=0.13) |
| **FUERA POI** | 112.401 | 50.7% (p=1.0) | 53.2% (p=0.96) | 53.7% (p=0.68) |

El gap EN_POI vs FUERA_POI es solo ~1.1pp (51.8 vs 50.7). En OTC 60s el CICLO-001
veía 71-84% vs 47% (gap ~25pp). **En M15 REAL el efecto POI se desvanece.**

### Ablación: LightGBM SIN feature POI
- AUC test 0.5206 (idéntico con POI) · top10 WR 53.2% (p=0.96) · top05 54.2% (p=0.37)
- Quitar POI no cambia nada → la red no usa POI para predecir.

## Feature importances (top 15 de 28)
```
hour        349   range_atr   248   atr_ratio  248   ret1     225
dist_ema160 219   dist_ema5   217   dist_ema80 187   lower_wick 182
dist_ema10  180   k          159   dist_ema20 148   ret20    148
dist_ema40  143   dist_ema320 139   upper_wick 139   k_slope1 129
```
**Lo que NO importa:** `in_poi`=87 (bajo), `arcoiris_stack`=**6** (cero), `k_extremo_lo/hi`=**0** (cero).
Las herramientas del Edificio (arcoíris, extremo stoch) aportan ~0 a la red en M15 real.

## MLP (modelo secundario)
- AUC test 0.518 · TEST global 50.7% (p=1.0) · top10 52.9% (p=0.995) · top05 53.4% (p=0.83).
- Consistente con LightGBM: sin edge.

## Veredicto (honesto, falsable)

**NO hay edge aprendible por redes neuronales en SPOT M15 REAL con estas herramientas.**

1. AUC ≈ 0.52 (azar). WR por decil ≤ 54.2%, ninguno significativo en TEST (p≥0.35).
2. El efecto POI que era fuerte en OTC 60s (CICLO-001: 71-84%) **NO se replica en M15 real** (gap ~1pp, no significativo).
3. Las herramientas del Edificio (arcoíris, extremo stoch, válvula) tienen importancia ~0; la red se apoya en ruido temporal (hour) y microestructura (wick/atr/ret1) que no generaliza a TEST con significancia.

Esto NO falsa el edge en OTC (EXP-076/077, CICLO-001 siguen en su dominio). Solo
establece que **la composición actual no es transportable a M15 REAL** — conclusión
más fuerte que CICLO-002 (que era "n=0 por insuficiencia"): aquí hay muestra enorme
(133k test) y el resultado es negativo con evidencia.

## Implicación para el Edificio
El gate enchufado (feature 40) sigue siendo válido como ARQUITECTURA; pero su
composición (arcoíris+válvula K/D) está calibrada para OTC 60s. Promover a REAL
requiere rediseñar la señal sobre M15 (o aceptar que el edge es dominio-OTC).

## Archivos
- `exp084_nn_spot_m15.py` — script reproducible (reusa exp_common.py)
- `_raw_results.json` — resultados crudos completos
- `REPORTE_EXP-084.md` — este archivo
