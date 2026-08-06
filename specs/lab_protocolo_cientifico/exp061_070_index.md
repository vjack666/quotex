# Indice EXP-061..EXP-070 (serie PIPELINE, EURUSD REAL)

| EXP | pipeline | entradas | WR | EV | p | p_adj_FDR | FDR |
|---|---|---|---|---|---|---|---|
| EXP-061 | freno | 13635 | 0.4957 | -0.5786 | 0.3205 | 0.000395 | SOBREVIVE |
| EXP-062 | freno>extremo | 2384 | 0.5264 | -0.5525 | 0.0104 | 0.000395 | SOBREVIVE |
| EXP-063 | freno>extremo>cruce | 2178 | 0.523 | -0.5555 | 0.0339 | 0.000395 | SOBREVIVE |
| EXP-064 | freno>extremo>cruce>separacion | 2088 | 0.4914 | -0.5823 | 0.4437 | 0.000395 | SOBREVIVE |
| EXP-065 | freno>extremo>cruce>separacion>martillo | 279 | 0.5018 | -0.5735 | 1.0000 | 0.000395 | SOBREVIVE |
| EXP-066 | extremo>freno>separacion>martillo>cruce | 898 | 0.431 | -0.6337 | 0.0000 | 0.000395 | SOBREVIVE |
| EXP-067 | freno>separacion>extremo>martillo>cruce | 229 | 0.4934 | -0.5806 | 0.8949 | 0.000395 | SOBREVIVE |
| EXP-068 | extremo>freno>martillo>cruce | 1600 | 0.4775 | -0.5941 | 0.0759 | 0.000395 | SOBREVIVE |
| EXP-069 | extremo>freno>cruce>martillo | 1763 | 0.5298 | -0.5497 | 0.0132 | 0.000395 | SOBREVIVE |
| EXP-070 | freno>separacion>extremo>cruce>martillo | 347 | 0.5274 | -0.5517 | 0.3339 | 0.000395 | SOBREVIVE |

**Veredicto:** todos sobreviven FDR (p_adj=0.000395) en significancia direccional,
pero EV neto NEGATIVO en todos (-0.55 a -0.63). Hay senal direccional real
(WR ~0.53) pero el costo de payout 0.85 la destruye.
MEJOR por EV: EXP-069 [extremo>freno>cruce>martillo] WR 0.530 EV -0.550 p_adj 0.000395.
