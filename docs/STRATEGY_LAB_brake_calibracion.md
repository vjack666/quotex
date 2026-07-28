# Calibración del freno (M2) — multi-activo, muerte del impulso

Pares: EURUSD, XAUUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY. Freno AISLADO (sin mezclar con otras primitivas).
54 combinaciones, 54 con n>=80.

Mejor por WR (n>=80):

| adv | alt | reb_fwd | reb_pip | n | WR | WR_train | WR_hold | n_up/WR_up | n_dn/WR_dn |
|-----|-----|---------|---------|---|----|----------|---------|-----------|-----------|
| 0.15 | True | 3 | 5 | 7,978 | 91.1% | 91.0% | 91.2% | 3965/90.9% | 4013/91.2% |
| 0.15 | True | 3 | 3 | 7,978 | 91.1% | 91.0% | 91.2% | 3965/90.9% | 4013/91.2% |
| 0.10 | True | 3 | 3 | 5,332 | 91.1% | 90.8% | 91.4% | 2685/91.4% | 2647/90.8% |
| 0.10 | True | 3 | 5 | 5,332 | 91.1% | 90.8% | 91.4% | 2685/91.4% | 2647/90.8% |
| 0.10 | True | 3 | 8 | 5,332 | 91.1% | 90.8% | 91.4% | 2685/91.4% | 2647/90.7% |
| 0.15 | True | 3 | 8 | 7,978 | 91.1% | 91.0% | 91.1% | 3965/90.9% | 4013/91.2% |
| 0.05 | True | 3 | 5 | 2,602 | 90.7% | 91.1% | 90.4% | 1296/91.0% | 1306/90.5% |
| 0.05 | True | 3 | 3 | 2,602 | 90.7% | 91.1% | 90.4% | 1296/91.0% | 1306/90.5% |
| 0.05 | True | 3 | 8 | 2,602 | 90.7% | 91.1% | 90.3% | 1296/91.0% | 1306/90.4% |
| 0.15 | True | 2 | 3 | 7,978 | 90.6% | 90.2% | 91.0% | 3965/91.1% | 4013/90.1% |
| 0.15 | True | 2 | 5 | 7,978 | 90.5% | 90.1% | 91.0% | 3965/91.1% | 4013/90.0% |
| 0.15 | True | 2 | 8 | 7,978 | 90.5% | 90.1% | 91.0% | 3965/91.1% | 4013/90.0% |

## Mejor combo: adv=0.15 alt=True reb_fwd=3 "
        f"reb_pip=5
  WR=91.1% (n=7,978) train=91.0% "
        f"holdout=91.2%

## WR por par (mejor combo)
- EURUSD: WR=100.0% (n=56)
- XAUUSD: WR=90.9% (n=6266)
- GBPUSD: WR=96.8% (n=31)
- AUDUSD: WR=100.0% (n=7)
- NZDUSD: WR=100.0% (n=2)
- USDCAD: WR=100.0% (n=16)
- USDCHF: WR=100.0% (n=8)
- USDJPY: WR=91.2% (n=1592)

## WR > 56% (umbral binarias): 54 de 54 combinaciones válidas
TODAS o casi todas pasan 56% -> la muerte del impulso (M2) es una SEÑAL DIRECCIONAL FUERTE en M15, alineada con LAB-001 (69.8% M1).
El smoke original la descartaba por contaminación al mezclarla con
impulso/sobrecompra. Aquí, aislada, el edge es masivo.
