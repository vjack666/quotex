# Estocástico en zona OS/OB — barrido MULTI-ACTIVO (no-OTC, sin filtro hora)

Pares: EURUSD, XAUUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY — 700,000 velas M15.
Filosofía: no-OTC se rige por estructura, no por sesión -> sin filtro de hora.

Mejores combinaciones por (WR × n>=1000 normalizado):

| os/ob | fwd | min_pip | sep | cruce | n | WR |
|-------|-----|---------|-----|-------|---|----|
| 15/85 | 3 | 1 | 0 | True | 20,506 | 44.9% |
| 15/85 | 3 | 1 | 2 | True | 16,290 | 44.6% |
| 20/80 | 3 | 1 | 2 | True | 16,384 | 44.6% |
| 20/80 | 3 | 1 | 0 | True | 19,394 | 44.5% |
| 20/80 | 3 | 1 | 2 | False | 47,381 | 44.5% |
| 10/90 | 3 | 1 | 0 | True | 17,616 | 44.5% |
| 20/80 | 3 | 1 | 0 | False | 52,447 | 44.5% |
| 15/85 | 3 | 1 | 0 | False | 45,106 | 44.4% |
| 10/90 | 3 | 1 | 0 | False | 31,503 | 44.3% |
| 20/80 | 3 | 1 | 5 | False | 34,208 | 44.3% |
| 15/85 | 3 | 1 | 2 | False | 38,320 | 44.3% |
| 20/80 | 3 | 1 | 5 | True | 9,988 | 44.2% |
| 15/85 | 3 | 1 | 5 | True | 8,157 | 44.0% |
| 10/90 | 3 | 1 | 2 | False | 23,134 | 44.0% |
| 10/90 | 3 | 1 | 5 | False | 8,608 | 43.9% |

## Mejor WR puro: os/ob=15/85 fwd=3 "
        f"min_pip=1 sep=0 cruce=True "
        f"-> WR=44.9% (n=20,506)

## WR por activo en esa mejor combinación
- EURUSD: WR=41.6% (n=6,032)
- XAUUSD: WR=49.1% (n=5,896)
- GBPUSD: WR=43.6% (n=1,423)
- AUDUSD: WR=44.2% (n=1,418)
- NZDUSD: WR=43.4% (n=1,415)
- USDCAD: WR=42.5% (n=1,492)
- USDCHF: WR=41.1% (n=1,414)
- USDJPY: WR=51.0% (n=1,416)

## Resumen
- Combinaciones: 162
- WR > 50%: 0 (0% del total)

Si hay combinaciones WR>50% con n suficiente, tu teoría del "empujón al salir
de zona" se CONFIRMA con data grande multi-activo. Si no, el empuje es
simétrico (existe pero no predice dirección) y sirve como filtro, no señal.
