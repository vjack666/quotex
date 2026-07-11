# Índice — Cómo se forman las velas (rastro del mercado)

> Libro 3 de la biblioteca. Complementa `wyckoff/` (fases A–E) y `fractales/`
> (giros de Bill Williams). Aquí el foco es el **suelo**: qué es una vela en
> realidad, cómo la construye el broker tick a tick, y por qué NO debe evaluarse
> como un evento aislado.

## Idea central (la regla de Ruben)
> "En binarias no quiero que todo se evalúe en una sola vela. El mercado se va
> formando y a su vez deja un rastro."

Una vela de 1 minuto no es "una decisión": es la **foto final** de miles de
micro-decisiones (trades) ocurridas durante ese minuto. El cuerpo y las mechas
son el **rastro** (footprint) de quién ganó la pelea compra/venta en el camino.
Por eso operamos leyendo la FORMACIÓN (varias velas) y el RASTRO (qué dejó
cada vela), no una vela suelta.

## Archivos
| Archivo | Contenido |
|---|---|
| `00_indice.md` | Este mapa. |
| `01_que_es_una_vela.md` | OHLC no son 4 números sueltos: son el resumen de un rastro. |
| `02_tick_a_vela.md` | Cómo el broker agrupa ticks en una vela (open/high/low/close). |
| `03_cuerpo_vs_mecha.md` | El cuerpo = quien dominó; la mecha = hasta dónde llegó y fue rechazado. |
| `04_el_rastro.md` | Por qué una vela "cuenta una historia" (order flow comprimido). |
| `05_no_una_sola_vela.md` | El principio de Ruben: formación + rastro, no vela aislada. |
| `06_aplicado_binarias.md` | Qué significa esto en M1/M5/M15 para nuestras entradas. |
| `07_gestion_riesgo.md` | No juzgar la vela en curso; esperar el cierre. |

## Fuentes consultadas
- Susan Potter — "Finding Signal in Market Noise" (microstructure, OHLC destruye
  el order flow; modelo event-sourced del order book).
- Order Flow Pro — "Beyond Candlesticks" (order flow analysis, footprint).
- J2T — "How to Read Candlestick Charts" (cuerpo = emoción dominante, mechas =
  presión en extremos).
- NinjaTrader — "Order Flow Trading" (footprint/volumetric bars, CVD, absorción,
  agotamiento/exhaustion).
