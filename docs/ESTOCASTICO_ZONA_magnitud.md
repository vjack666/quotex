# Magnitud del empuje estocástico al salir de zona — 8 pares no-OTC

Pares: EURUSD, XAUUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY. Sin filtro de hora (no-OTC = estructura).
ratio = |movimiento| post-salida / |movimiento| base aleatoria. ratio>1 = hay
empujón real de volatilidad; p_value<0.05 = no es azar.

Mejores por ratio (top 15):

| os/ob | fwd | sep | cruce | n | |salida| | |base| | ratio | p |
|-------|-----|-----|-------|---|--------|-------|-------|---|
| 10/90 | 1 | 2 | False | 31,504 | 4111.54 | 4017.91 | 1.023 | 0.403 |
| 10/90 | 1 | 0 | False | 31,504 | 4111.54 | 4047.60 | 1.016 | 0.410 |
| 20/80 | 1 | 5 | False | 52,449 | 4507.59 | 4465.54 | 1.009 | 0.227 |
| 10/90 | 2 | 5 | True | 31,503 | 5779.10 | 5733.22 | 1.008 | 0.477 |
| 10/90 | 1 | 5 | False | 31,504 | 4111.54 | 4085.00 | 1.006 | 0.389 |
| 20/80 | 2 | 0 | False | 52,447 | 6386.45 | 6349.11 | 1.006 | 0.210 |
| 20/80 | 2 | 5 | False | 52,447 | 6386.45 | 6350.93 | 1.006 | 0.229 |
| 20/80 | 3 | 5 | True | 52,447 | 7842.11 | 7799.14 | 1.006 | 0.232 |
| 15/85 | 2 | 5 | True | 45,106 | 6174.32 | 6148.06 | 1.004 | 0.238 |
| 15/85 | 2 | 0 | True | 45,106 | 6174.32 | 6150.04 | 1.004 | 0.244 |
| 10/90 | 2 | 0 | True | 31,503 | 5779.10 | 5764.00 | 1.003 | 0.467 |
| 20/80 | 2 | 2 | True | 52,447 | 6386.45 | 6378.76 | 1.001 | 0.203 |
| 10/90 | 2 | 5 | False | 31,503 | 5779.10 | 5789.18 | 0.998 | 0.494 |
| 20/80 | 3 | 2 | True | 52,447 | 7842.11 | 7861.05 | 0.998 | 0.234 |
| 10/90 | 1 | 0 | True | 31,504 | 4111.54 | 4122.51 | 0.997 | 0.426 |

## Mejor combo: os/ob=10/90 fwd=1 "
        f"sep=2 cruce=False
  |salida|=4111.54 pip | |base|=4017.91 pip
  ratio=1.023 p=0.403

## Lectura
- 0 de 54 combinaciones tienen ratio>1.1 (empujón >10% sobre base).
- Si hay combos con ratio>1.1 Y p<0.05: tu "empujón al salir de zona" es REAL
  como explosión de volatilidad -> úsalo para breakouts, no como señal direccional.
- Si todos los ratio~1 y p~1: el movimiento post-salida es indistinguible del
  ruido -> el empuje que ves es efecto de tu selección (sesgo de confirmación).
