# LAB-UNIVERSALIDAD — La muerte del empuje es propiedad del mercado

Fecha: 2026-07-27 · Laboratorio · Estado: VALIDADO
Reproducir: `PYTHONPATH=src python scripts/universalidad_lab.py`
Cruza LAB-001 (muerte del empuje) y LAB-002 (zona grande) sobre 9 pares.
Metodología: máquina de estados local transitions_v1 leyendo parquet SMC-SYSTEMS
(reescrita en el script; no depende de la DB del Atlas). PIP por activo.
n total ≈ 300,000 episodios.

## Resultados MUERTE DEL EMPUJE → % REBOUND
| Par            | n(ep)  | MUERTE | resto | vivo | walk-f 12-19 / 20-26 |
|----------------|--------|--------|-------|------|----------------------|
| XAUUSD_M1      | 68,034 | 76.8%  | 19.1% | 12.6%| 73.3 / 77.4          |
| EURUSD_M5      | 25,748 | 75.2%  | 19.9% | 13.4%| 73.9 / 76.8          |
| NZDUSD_M5      | 26,480 | 74.1%  | 18.3% | 13.5%| 72.6 / 75.8          |
| GBPUSD_M5      | 26,336 | 73.2%  | 18.5% | 13.0%| 73.0 / 73.4          |
| USDCAD_M5      | 26,383 | 73.3%  | 18.6% | 13.5%| 72.2 / 74.6          |
| XAUUSD_M5      | 26,409 | 72.9%  | 18.6% | 14.3%| 72.3 / 73.8          |
| USDCHF_M5      | 26,067 | 72.4%  | 18.8% | 13.5%| 71.3 / 73.7          |
| USDJPY_M5      | 26,569 | 72.5%  | 19.2% | 14.4%| 71.5 / 73.8          |
| AUDUSD_M5      | 32,867 | 72.3%  | 17.7% | 13.1%| 71.3 / 74.2          |

LAB-002 ZONA GRANDE vs CHICA: en todos los pares GRANDE 34-38% vs CHICA 18-21%.
Placebo p<0.001 en oro y AUDUSD (barajadas 1,000x).

## Veredicto
La señal NO es de un activo: es de un COMPORTAMIENTO del mercado. 72-77% de
rebote donde el impulso muere del todo, 12-14% si sigue vivo, en FX y oro,
estable en walk-forward en CADA par. Esto es lo que hace al hallazgo
estratégico, no el 76% aislado: modela psicología de mercado, no un símbolo.

## Implicación para el negocio
El fenómeno es agnóstico al vehículo (PTM v3): binarias (¿ganó en 5/15 min?),
FX (¿TP 20 pips?), futuros (¿3R?), acciones (¿swing?) — todas consumen la
misma película del episodio. El Atlas (no el bot) es el activo difícil de
replicar.
