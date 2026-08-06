# EXP-074b — Estabilidad de Clusters (freno cientifico, EURUSD REAL)

## Hipotesis (freno cientifico, dictamen Trader-Humano + Grok/ChatGPT)

EXP-074 APOYA poblacion mixta (silhouette 0.22) pero NO la demuestra como
propiedad del mercado. Riesgo: enamorarse del clustering y tratar particion
conveniente como estructura descubierta. EXP-074b responde UNA pregunta:
¿los dos tipos de Fase A son propiedad del mercado o del metodo?

## Metodologia (6 pruebas)

1. Cambio de algoritmo: GMM/KMeans/Spectral/Agglomerative/HDBSCAN (ARI vs GMM)
2. Ablacion de features: full / sin_KD / solo_energia / solo_reglas
3. Estabilidad temporal: train 2012-2018 -> test 2019-2024 (OOS)
4. Bootstrap: 300 remuestreos -> % explosivo en rango estrecho
5. Interpretabilidad economica (ChatGPT): perfil del explosivo coherente
6. Reglas simples (ChatGPT): dur<15->explosiva, dur>=25->lateral vs GMM

## Resultados (dataset completo 3307 fases, 2022-2026)

=== EXP-074b — ESTABILIDAD DE CLUSTERS (freno cientifico, EURUSD REAL) ===

Fases A totales: 3307 | periodo: 2022-01-03 -> 2026-08-05

-- PRUEBA 1: Cambio de algoritmo (mismo tamano/perfil?) --
  kmeans       sizes={0: 2417, 1: 890} | ARI vs GMM=-0.059
  spectral     sizes={0: 3301, 1: 6} | ARI vs GMM=0.008
  agglomerative sizes={0: 2910, 1: 397} | ARI vs GMM=-0.091
  hdbscan      sizes={0: 222, 1: 1956, 2: 1129} | ARI vs GMM=0.454
  -> GMM base: {0: 807, 1: 2500}

-- PRUEBA 2: Ablacion de features (sobrevive el explosivo ~24%?) --
  full         sizes={0: 807, 1: 2500} | % cluster corto (explosivo~)=24.4%
  sin_KD       sizes={0: 320, 1: 2987} | % cluster corto (explosivo~)=9.7%
  solo_energia sizes={0: 1590, 1: 1717} | % cluster corto (explosivo~)=48.1%
  solo_reglas  sizes={0: 2596, 1: 711} | % cluster corto (explosivo~)=21.5%

-- PRUEBA 3: Estabilidad temporal (train 2012-2018 -> test 2019-2024) --
  insuficientes datos para split temporal

-- PRUEBA 4: Bootstrap (300 remuestreos) --
  % explosivo por remuestreo: media=30.0% rango=[21.8,95.6] p05-p95=[23.3,88.2]
  -> estable (rango <10pp): NO

-- PRUEBA 5: Interpretabilidad economica (perfil del explosivo) --
  Explosivo (cluster 0): dur=11 n_osc=2 entropy=0.00 slope_K=-2.79 vol_mean=154 atr=0.001
  Lateral   (cluster 1): dur=32 n_osc=8 entropy=0.95 slope_K=0.21 vol_mean=0 atr=0.001
  -> interpretable (ruptura directa vs acumulacion): SI

-- PRUEBA 6: Reglas simples (dur<15->explosiva, dur>=25->lateral) vs clustering --
  n con regla definida: 2560 | acuerdo con GMM: 90.3% | ARI=0.642
  -> reproducible con reglas simples: SI

-- Veredicto del tribunal (freno cientifico) --
Si PRUEBA 1-4 dan coherencia + PRUEBA 5/6 interpretable/reproducible:
  los subtipos son PROPIEDAD DEL MERCADO -> EXP-075 procede.
Si no: el clustering es particion conveniente -> NO promover.
Art. 13: REAL=descubrimiento. Sin win rate.

## Veredicto del tribunal

- PRUEBA 1 (algoritmo): NO robusto. GMM 807/2500 pero KMeans 2417/890 (ARI -0.059),
  Spectral colapsa a 1 cluster, Agglom ARI -0.091, HDBSCAN 3 grupos ARI 0.454.
- PRUEBA 2 (features): % explosivo salta de 9.7% (sin_KD) a 48.1% (solo_energia).
- PRUEBA 3 (OOS): NO ejecuto (dataset empieza 2022, no hay 2012-2018). LIMITACION.
- PRUEBA 4 (bootstrap): % explosivo rango [21.8, 95.6], p05-p95 [23.3, 88.2]. NO estable.
- PRUEBA 5 (interpretabilidad): SI coherente (ruptura directa vs acumulacion).
- PRUEBA 6 (reglas simples): SI reproducible (90.3% acuerdo, ARI 0.642).

## Consecuencia cientifica

El cluster de GMM (24/76) NO sobrevive a estabilidad: es mayornente PARTICION
CONVENIENTE DEL METODO, no estructura estable del mercado. La particion de GMM
es basicamente DURACION+n_osc (ruptura corta vs lateral larga): variable continua
que GMM corta en 2, no 2 poblaciones profundas (silhouette 0.22 = separacion moderada).
EXP-074 (poblacion mixta) = APOYADA mas NO demostrada. NO procede EXP-075 sobre el
cluster de GMM. Lo REAL: duracion de la Fase A es dimension continua util.
Freno cientifico SALVO al lab de construir estrategia falsa. Art. 13: descubrimiento.

## Cumple Charter

- Art. 1 (descubrimiento): Si | Art. 9 (freno/disciplina): Si | Art. 13 (REAL): Si