# Validation — EXP-074b-NULL (control nulo + temporal OOS)

> Consume el tribunal. Cierra el hilo del clustering (junto a 074b). Veredicto: NO SOPORTADA.

## Resultados (EURUSD REAL, 3307 Fases A, 2022-2026)
- **REAL (GMM n=2)**: silhouette=0.2185 | %minoritario=24.4% | structure score=0.487
  - c0 (corto/explosivo): dur=11, n_osc=2, entropy=0, slope_K=-2.79
  - c1 (largo/lateral):   dur=32, n_osc=8, entropy=0.95, slope_K=0.21
- **NULL (shuffle independiente por feature, B=200)**:
  - silhouette null: media=0.4048, p05=0.3564, p95=0.4587
  - %minoritario null: media=2.9%, rango=[0.5, 21.6]
  - structure score null: media=0.138, p95=0.230
  - fracción de null con silhouette > REAL: **0.970**
  - fracción de null con structure score > REAL: **0.000**
  - ARI(REAL, null)=0.006 (≈0 → particiones distintas)
- **KMeans REAL**: silhouette=0.1952 (menor que GMM, robusto al método: baja separabilidad)
- **PRUEBA TEMPORAL OOS** (TRAIN 2022-2024 n=2066 → TEST 2025-2026 n=1241):
  - TRAIN %corto=18.2% | TEST %corto=**100.0%** | diff=**81.8pp**
  - silhouette TEST (predicho con GMM de TRAIN) = **nan** (un solo cluster → colapso)

## RETRACCIÓN / matiz metodológico honesto (obligatorio)
Mi protocolo congelado (hypothesis_exp074b_null.md) fijó el criterio:
"estructura real SI sil_REAL>p95_null AND ss_REAL>p95_null". El resultado fue MIXTO:
- sil_REAL(0.2185) > p95_null(0.4587) → **NO**
- ss_REAL(0.487) > p95_null(0.230) → **SÍ**

NO voy a torcer el veredicto hacia "estructura real" usando el structure score aislado.
Razón: el null de **shuffle independiente de columnas es un null FUERTE que GENERA
geometría favorable**. Al des-correlacionar las 19 features, cada una queda como eje
independiente y GMM recorta limpio en alguna → silhouette del null ALTA (0.40). Por eso
el 97% de los null superan al REAL en silhouette. Es decir: silhouette NO es la métrica
correcta para refutar contra este null (el null es geométricamente más favorable, no menos).
El structure score del REAL supera al null SOLO porque el null, por construcción, destruye
justo las correlaciones que producen el perfil (dur corta + n_osc baja + entropy 0). El
null no PUEDE reproducir ese perfil porque lo borré al barajar. Punto débil del null, no
evidencia de régimen.

**La evidencia DECISIVA no es el null, es la OOS temporal + lo ya hallado en 074b:**
1. **OOS colapsa**: el GMM entrenado en 2022-2024 clasifica el 100% de 2025-2026 como
   "corto". Si hubiera regímenes naturales estables, TEST debería ser coherente (diff<8pp).
   diff=81.8pp → NO hay estabilidad temporal. (Silhouette TEST=nan confirma colapso.)
2. **% minoritario**: REAL 24.4% está en el BORDE SUPERIOR del null (null máx=21.6%).
   El null lo explica casi tan bien → la proporción no es propiedad exclusiva del mercado.
3. **074b previo (ya ejecutado)**: ARI≈0 entre 5 algoritmos; ablación cambia minoritario
   9.7%→48.1%; bootstrap rango 22%→95%. Tres pruebas independientes de no-robustez.

## Conclusión (tribunal)
- **Hipótesis de población mixta: NO SOPORTADA** como estructura estable del mercado bajo
  este espacio de representación (19 features estocástico/dinámica de Fase A).
- **Distinción explícita**: "el clustering encuentra geometría" (SÍ, silhouette 0.22 =
  geometría real del espacio) ≠ "el mercado posee regímenes naturales" (NO demostrado;
  OOS colapsa, ablación lo destruye, método lo ignora).
- El K=2 de EXP-074 es una **conveniencia de recorte geométrico**, no dos poblaciones del
  mercado. Coincide con la intuición de Grok/ChatGPT validada por el Trader-Humano:
  "¿el mercado sigue produciendo estos tipos cuando cambiamos la forma de medirlos?" → NO.
- **EXP-075 (continuo de duración predictivo): RESULTADO NEGATIVO** documentado (FDR 0/36,
  OR por cuartil ≈1.0, OOS plano). Cierra también esa vía.

## Costo operacional / Art. 13
Sin win rate. Descubrimiento. No se promueve al Edificio. El hilo del clustering queda
CERRADO: no hay subtipos estables, ni binarios (074b) ni continuos (075).

## Límite del null (para futuros labs)
El shuffle independiente de columnas es null "fuerte". Un null más agudo sería preservar
la correlación INTRA-fase pero destruir la separación ENTRE-fases (ej. permutar solo las
etiquetas de fase, o surrogate de fase completa). No cambia el veredicto (la OOS ya lo
decide), pero se documenta para mejorar el diseño de nulls en el lab.

> Este experimento cumple el Charter: Sí
