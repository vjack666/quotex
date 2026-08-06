# EXP-072 — Mapa de Transiciones de Mercado (Markov sobre estados)

## Hipotesis (dictamen Trader-Humano 2026-08-06, paradigma Wyckoff)

El mercado NO es 'contexto -> confirmador -> entrada' (vela magica). Es
'estado -> transicion de estado -> confirmacion -> operacion'. El estocastico
ES el indicador de fase; el freno es la 1a reaccion (Spring de Fase A). Se
modela el mercado como estados (regime K x pendiente x impulso) y se descubre
el grafo de transiciones y que rutas llevan a movimientos favorables. Salida =
grafo + descriptores de Fase A, NO un win rate unico.

## Metodologia

- Dominio: EURUSD REAL (Art. 13: solo descubrimiento).
- Estado = (OS/OB/LO/HI/MID) x (up/dn/flat pendiente K) x (call/put/flat impulso).
- Grafo P(siguiente estado | estado) sobre toda la serie M15.
- Favorable: impulso del estado se realiza en H=4 velas (1h); binomial + FDR (Art. 9).
- Fase A: tras cada extremo, descriptores de comportamiento del estocastico.
- Payout/seed no aplican (no es estrategia unitaria).

## Resultados — Grafo (top transiciones)

 from_state   from_label  to_state    to_label  count    prob
         11   OB.up.flat        11  OB.up.flat   5364 0.54286
          5   OS.dn.flat         5  OS.dn.flat   4861 0.53500
         20   LO.up.flat        20  LO.up.flat   5853 0.51369
         32   HI.dn.flat        32  HI.dn.flat   5772 0.50393
         23   LO.dn.flat        23  LO.dn.flat   5656 0.50009
         29   HI.up.flat        29  HI.up.flat   5624 0.49459
         14   OB.dn.flat        14  OB.dn.flat   3117 0.46035
         38  MID.up.flat        38 MID.up.flat   4750 0.45845
         41  MID.dn.flat        41 MID.dn.flat   4588 0.45020
          2   OS.up.flat         2  OS.up.flat   2801 0.45018
          8 OS.flat.flat         2  OS.up.flat   1867 0.41223
         17 OB.flat.flat        14  OB.dn.flat   1976 0.41132

## Resultados — Estados por tasa favorable (H=4)

 state         label     n  favorable_rate       p_value  p_adj_fdr
    17  OB.flat.flat  4804          0.2968 2.114273e-179        0.0
    35  HI.flat.flat  2553          0.2949  5.347313e-98        0.0
    29    HI.up.flat 11371          0.2899  0.000000e+00        0.0
    14    OB.dn.flat  6771          0.2887 4.191736e-273        0.0
    41   MID.dn.flat 10191          0.2859  0.000000e+00        0.0
    44 MID.flat.flat  1809          0.2847  3.612474e-77        0.0
    11    OB.up.flat  9881          0.2836  0.000000e+00        0.0
    38   MID.up.flat 10361          0.2829  0.000000e+00        0.0
    26  LO.flat.flat  2500          0.2828 6.801956e-108        0.0
     2    OS.up.flat  6222          0.2811 4.197552e-270        0.0

Estados con sesgo favorable significativo (FDR, rate>0.55): 0

## Resultados — Fase A (tras cada extremo, n=3320)

duration          25.00
t_first_brake      6.00
t_first_cross      2.00
t_back_extreme     2.00
n_cross            5.00
n_brake            3.00
max_kd_sep        15.22
mean_kd_sep        5.30
mean_slope        -0.02

## Veredicto del tribunal

- Régimen persiste (auto-bucle 0.50-0.54): EURUSD es mean-reverting en estado.
- Impulso del estocastico SE REVIERTE (rate favorable 0.28-0.30), no se realiza.
- Fase A: ~25 velas (6h), 1er freno a 6, 1er cruce a 2, ~5 cruces, ~3 frenos,
  separacion K-D max 15.2, pendiente -0.02 (oscila en rango = acumulacion/distribucion).
- 0 estados con favorable_rate>0.55: NO hay estado ganador, pero SI sesgo real
  (reversion del impulso, p~0). Es el MAPA, no una estrategia.

## Consecuencia cientifica

El lab dejo de buscar la vela magica: descubrio que el mercado es mean-reverting
de regimen y que el impulso se revierte. Siguiente paso (cadena de Markov): operar
el sesgo de REVERSION del impulso, no seguirlo. Construir entrada SOBRE este mapa.

## Cumple Charter

- Art. 1 (descubrimiento): Si | Art. 9 (FDR): Si | Art. 13 (REAL=descubrimiento): Si