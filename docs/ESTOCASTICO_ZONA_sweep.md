# Estocástico en zona OS/OB — barrido binario 15 min (EURUSD M15, 14 años)

Corrección: el empuje se mide en la SALIDA de la zona, horizonte = fwd velas M15.
Señal: %K sale de OS (alcista) u OB (bajista); opcional |K-D|>=sep y/o cruce en
la salida. Win = precio se mueve >= min_pips en el sentido del empuje en fwd velas.

Total combinaciones: 162. Mejores por (wr × n>=500 normalizado):

| os/ob | fwd | min_pip | sep | cruce | n | WR | WR_OS | WR_OB |
|-------|-----|---------|-----|-------|---|----|-------|-------|
| 15/85 | 3 | 1 | 2 | True | 4,805 | 42.1% | 42.4% | 41.7% |
| 10/90 | 3 | 1 | 2 | False | 6,648 | 41.7% | 41.8% | 41.7% |
| 20/80 | 3 | 1 | 2 | True | 4,825 | 41.7% | 42.4% | 41.0% |
| 20/80 | 3 | 1 | 5 | False | 9,991 | 41.7% | 42.4% | 41.1% |
| 15/85 | 3 | 1 | 0 | True | 6,032 | 41.6% | 42.2% | 41.1% |
| 10/90 | 3 | 1 | 0 | False | 9,058 | 41.6% | 41.7% | 41.4% |
| 20/80 | 3 | 1 | 2 | False | 13,819 | 41.6% | 42.2% | 41.0% |
| 20/80 | 3 | 1 | 0 | True | 5,675 | 41.5% | 42.0% | 41.0% |
| 20/80 | 3 | 1 | 0 | False | 15,248 | 41.5% | 42.0% | 41.0% |
| 10/90 | 3 | 1 | 0 | True | 5,124 | 41.3% | 40.5% | 42.1% |
| 15/85 | 3 | 1 | 2 | False | 11,182 | 41.3% | 41.5% | 41.1% |
| 10/90 | 3 | 1 | 2 | True | 3,594 | 41.3% | 40.7% | 41.8% |
| 20/80 | 3 | 1 | 5 | True | 2,931 | 41.2% | 41.6% | 40.9% |
| 10/90 | 3 | 1 | 5 | True | 1,204 | 41.2% | 41.1% | 41.3% |
| 15/85 | 3 | 1 | 0 | False | 13,183 | 41.1% | 41.5% | 40.7% |

## Mejor WR puro: os/ob=15/85 fwd=3 "
        f"min_pip=1 sep=2 "
        f"-> WR=42.1% (n=4,805)

## Desglose por lado (todas las combinaciones)
- Media WR salida OS (alcista): 31.5%
- Media WR salida OB (bajista): 31.6%
- WR > 50% en 0 de 162 combinaciones.

Si alguna combinación da WR > 50% con n suficiente (>=200), tu teoría del
"empujón al salir de la zona" QUEDA REGISTRADA CON NÚMEROS para binarias de 15 min.
