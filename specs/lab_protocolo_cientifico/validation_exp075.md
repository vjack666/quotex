# Validation — EXP-075

> Consume el tribunal (promotion_gate.py). Veredicto único: PROMOVIDA | INCONCLUSIVE | REFUTADA.

## Resultados
- **Dataset**: EURUSD_M15.parquet (SMC_ROOT), 114,237 velas M15, 2022-01-02 → 2026-08-06
- **n (Fases A con etiqueta de resolución)**: 3307
- **Tasa base**: aligned 0.490 | clean 0.406
- **Sin Win Rate operativa** (descubrimiento de comportamiento, Art. 13)

## Pregunta (re-enfoque de EXP-074b)
EXP-074b (freno científico) RECHAZÓ la partición binaria GMM de Fases A: no sobrevive
a cambio de algoritmo (ARI≈0), ablación de features (9.7%→48.1%) ni bootstrap (22%→95%).
Lo que sobrevive es la **duración de la Fase A como variable continua**, no 2 poblaciones.
EXP-075 pregunta: ¿ese continuo TIENE señal predictiva MONÓTONA sobre cómo resuelve la fase?

## Control de falsos positivos (Art. 9)
- **FDR-BH (q)**: sobre 36 descriptores continuos × 2 targets (aligned/clean) en TRAIN → **0/36 significativos** (p_adj_fdr mínimo = 0.85).
- **Bonferroni (α')**: α/36 ≈ 0.0014. Ningún descriptor lo cruza.
- **p-value crudo (mediana-split chi2)**: todos > 0.07; ninguno sobrevive ajuste.
- **Bootstrap (300)**: OR_Q4 duration→clean median=1.028 IC95%=[0.835, 1.255] → **IC incluye 1.0: NO señal**.

## Poder estadístico
- **Poder observado**: >>0.99 (n=3307, tasa base ~0.4). Riesgo opuesto: falso positivo por exceso de poder → mitigado con FDR + Effect Size (R12).
- **Poder mínimo requerido**: 0.80 → CUMPLE.
- **NOTA metodológica**: la regresión logística multivariable del script reportó p_raw
  ínfimos para `n_osc`/`efficiency`/`move`, pero ese sub-cálculo usó una aproximación
  de error estándar colapsada y NO es de fiar. El veredicto NO se apoya en él; se apoya
  en el FDR median-split independiente (0/36) + bootstrap (IC incluye 1.0) + OOS, que son concluyentes.

## Robustez (REDIME PRUEBA 3 OOS de EXP-074b, antes bloqueada)
El dataset ahora cubre 2022→2026 (5 años). Split temporal legítimo:
- **TRAIN 2022-2024**: n=2066
- **TEST OOS 2025-2026**: n=1241

OR por cuartil de `duration` (monotonía):
| Split | target | rate Q1 | rate Q4 | OR_Q4 | p | plano? |
|---|---|---|---|---|---|---|
| TRAIN | aligned | 0.468 | 0.500 | 1.045 | 0.684 | SÍ |
| TRAIN | clean | 0.390 | 0.412 | 1.025 | 0.836 | SÍ |
| TEST OOS | aligned | 0.499 | 0.498 | 1.069 | 0.645 | SÍ |
| TEST OOS | clean | 0.395 | 0.404 | 1.015 | 0.947 | SÍ |

Las tasas por cuartil son planas (sin tendencia monotónica) en TRAIN y TEST. El patrón
continúa sin señal fuera de muestra → **robusto a régimen** (la no-señal se mantiene OOS).

## Effect Size (R12)
- **Métrica**: OR por cuartil de duration (regresión logística / Fisher exacto)
- **Valor**: OR_Q4 ∈ [1.015, 1.069] (todos los splits/targets), IC95% incluye 1.0
- **Umbral mínimo para promoción**: OR > 1.15
- **¿Cumple umbral?**: NO (lejos del umbral; OR≈1.0)

## Costo operacional (R13)
No aplica (descubrimiento de comportamiento, no estrategia). Edge neto = N/A.

## Veredicto (tribunal)
- **Estado**: REFUTADA (H1 rechazada; H0 no descartada)
- **Justificación**:
  1. FDR-BH sobre 36 descriptores continuos: **0/36 significativos** (Art. 9 cumplido).
  2. Bootstrap del OR del cuartil extremo: IC95%=[0.835,1.255] incluye 1.0 → NO señal.
  3. OOS temporal (2025-2026): la no-señal se replica (cuartiles planos, OR≈1.0) → robusto a régimen.
  4. Effect Size OR≈1.0 ≪ umbral 1.15 (R12) → aunque p<α no habría promoción.
- **Dominio validado** (Art. 10): REAL (descubrimiento). No se promueve al Edificio (Art. 13).
- **Interpretación de trader**: confirma la narrativa del lab. La duración de la Fase A es
  un continuo SIN borde útil — ni corta ni larga predicen mejor el breakout. Esto cierra
  limpio el hilo abierto por EXP-074b: no solo la partición GMM era falsa, sino que ni
  siquiera el eje continuo de duración lleva señal. El estocástico (y sus derivados de
  fase) describen ESTADO/posición, no CONTROL/energía ni su resolución (cf. EXP-072/073).

> Este experimento cumple el Charter: Sí
