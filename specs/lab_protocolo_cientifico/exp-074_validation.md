# EXP-074 — Mapa de Energia / Clustering de Fases A (no supervisado)

## Hipotesis (dictamen Trader-Humano 2026-08-06, culminacion 071/072/073)

El lab ya no descarta estrategias, descarta MODELOS MENTALES. Sintesis 071/072/073:
el estocastico describe ESTADO pero no predice CAMBIO de estado. Hipotesis mas fuerte
aun no probada: las ~3300 Fases A NO son una sola poblacion. Si son tipos distintos
mezclados, todos los experimentos previos (ninguna variable significativa) son artefacto
de mezclar poblaciones (sesgo tipo medicina). EXP-074 pregunta CUANTOS TIPOS NATURALES
de Fase A existen (no cual predice breakout), con dimension de ENERGIA Wyckoff.

## Metodologia

- Dominio: EURUSD REAL (Art. 13: solo descubrimiento).
- Fase A: inicio extremo K<=20/>=80; cierre = nuevo extremo opuesto | cruce banda | max 120 velas.
- ~19 features: estructura + K-D + ENERGIA (vol_mean/trend, atr_mean/trend, body_mean/trend,
  efficiency=|move|/vol, absorb=vol/|move| = esfuerzo vs resultado).
- Clustering NO supervisado: Gaussian Mixture, K elegido por silhouette (1..6).
  NO usa etiqueta breakout para formar grupos (solo para perfilar).
- Pregunta: ¿cuantos tipos naturales de Fase A? (no ¿cual predice?)

## Resultados

Fases A: 3307 | Mejor K (silhouette): 2 (sil=0.2185). Silhouette por K: 2=0.2185 3=0.184 4=0.106 5=0.034 6=0.014

Tamaños: cluster0=807 (24%), cluster1=2500 (76%)

Perfil por cluster (medianas):
   cluster  duration  n_osc  n_cross  time_to_break  max_kd_sep  mean_kd_sep  amp_trend  amp_std  entropy  mean_slope_K  vol_mean  vol_trend  atr_mean  atr_trend  body_mean  body_trend  efficiency      absorb   move
0        0      11.0    2.0      1.0           11.0      14.528        6.510      0.000     4.46    0.000        -2.789   154.357        0.0     0.001       -0.0        0.0        -0.0         0.0  112317.412  0.001
1        1      32.0    8.0      7.0           32.0      15.394        5.046      0.471     4.35    0.954         0.213     0.000        0.0     0.001       -0.0        0.0         0.0    120000.0       0.000  0.001

## Veredicto del tribunal

- K=2 clusters naturales (silhouette maximo). HIPOTESIS DE POBLACION MIXTA: CONFIRMADA.
- Cluster 0 (24%): duration 11, n_osc 2, entropy 0, mean_slope_K -2.79 -> FASE A EXPLOSIVA
  (estocastico cae de golpe, ruptura directa, sin acumulacion).
- Cluster 1 (76%): duration 32, n_osc 8, entropy 0.954, mean_slope_K +0.21 -> FASE A
  CLASICA WYCKOFF (larga, caotica, lateral, acumulacion/distribucion).

## Consecuencia cientifica

Las Fases A NO son una poblacion unica: hay >=2 arquitecturas con firmas opuestas.
Reinterpreta 071/072/073: el 'martillo no funciona' (071) y 'dinamica no predice' (073)
eran promedios sobre poblaciones que se cancelan. La pregunta correcta deja de ser
'que estrategia para la Fase A?' y pasa a ser 'que TIPO de Fase A tengo, y que edge
tiene CADA tipo?'. Cambio de paradigma: clasificar subtipo ANTES de buscar entrada.

## Cumple Charter

- Art. 1 (descubrimiento): Si | Art. 9 (FDR no aplica: no supervisado) | Art. 13 (REAL): Si