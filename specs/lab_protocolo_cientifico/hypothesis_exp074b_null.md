# Hypothesis — EXP-074b-NULL (control nulo / surrogate)

> Complementa EXP-074b (freno cientifico). Cumple docs/LAB_CHARTER.md.
> PROTOCOLO CONGELADO ANTES DE CORRER (Art. 6). No se ajusta el metodo post-hoc.

## Identificación
- **ID**: EXP-074b-NULL
- **Titulo**: ¿La estructura de 2 poblaciones en Fase A (EXP-074) excede la geometria del metodo bajo ausencia de estructura conjunta?
- **Dominio**: REAL (descubrimiento, Art. 13). Sin win rate.

## Antecedente
EXP-074 encontro K=2 con sil 0.2185 y proporciones 24/76 (explosivo/clasico).
EXP-074b (algoritmo/ablation/bootstrap/temporal-bloqueada/interpretabilidad/reglas)
RECHAZO: ARI~0 entre metodos, ablacion cambia minoritario 9.7%->48.1%, bootstrap
rango 22%->95%. El rechazo sugiere que la particion es geometria del metodo, no
regimen del mercado. EXP-074b-NULL lo DEMUESTRA con un grupo control.

## Hipotesis
- **H0 (nula)**: la particion observada es indistinguishable de la que produce el MISMO
  pipeline sobre datos donde se preservan las distribuciones marginales de cada feature
  pero se DESTRUYE la dependencia conjunta (correlaciones cruzadas entre features de la
  Fase A). Es decir: el clustering encuentra geometria, no regimen del mercado.
- **H1 (estructura real)**: la separabilidad/silhouette/perfil de EXP-074 excede el rango
  que produce el null -> hay correlacion conjunta que el mercado mantiene y el null no.

## Metodo (no ajustado post-hoc)
- Dataset: EURUSD_M15 (SMC_ROOT), mismo pipeline de features que EXP-074/074b/075.
- Features: 19 (NUM_COLS de 074b). Estandarizacion StandardScaler idéntica.
- Surrogate: por cada feature, permutar filas INDEPENDIENTEMENTE (shuffle de indices).
  Preserva marginal exacta de cada feature; anula toda correlacion cruzada.
  B = 200 remuestreos.
- Pipeline sobre cada null: GMM(n=2, seed=42) -> etiquetas, silhouette, proporcion
  minoritaria, "structure score" (media de |mediana_c0 - mediana_c1|/std por feature),
  ARI vs particion REAL.
- Tambien KMeans(n=2) para robustez de metodo.

## Métricas de comparacion
1. silhouette REAL vs distribucion null (media, p95, fraccion de null con sil > sil_REAL).
2. structure score REAL vs distribucion null (diferencia de perfil economico).
3. ARI REAL vs null (esperado ~0 si son particiones distintas).
4. proporcion minoritaria REAL (24%) vs rango null.

## Criterio de rechazo de H0 (estructura del mercado)
REAL se considera estructura del mercado SOLO si TODAS se cumplen:
- sil_REAL > percentil 95 de sil_null, Y
- structure_score_REAL > percentil 95 de null, Y
- ARI REAL-vs-null ~ 0 (la particion real NO es la del null).
Si sil_REAL cae DENTRO del rango null (p > 0.05 de los null superan a REAL) ->
la particion es ARTEFACTO GEOMETRICO. Se reporta la diferencia que sobrevive (si hay).

## Relacion con la orden
Cierra el hilo del clustering (junto a 074b temporal OOS). No busca edge. No promueve
a estrategia (Art. 13). Distinguir siempre "clustering encuentra geometria" de
"mercado posee regimenes naturales".
