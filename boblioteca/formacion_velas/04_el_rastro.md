# 4 · El rastro (order flow comprimido)

Susan Potter usa una analogía de ingeniería que aplica perfecto a nuestro bot:
el order book es una estructura **event-sourced**. El estado actual es la
proyección de todos los eventos (add/modify/cancel de órdenes). La vela OHLC es
lo que queda cuando **tiras el log de eventos y guardas solo la foto final**.

Traducido a binarias:
- Cada vela deja un **rastro**: dónde estuvo el precio, quién lo empujó, dónde lo
  rechazaron.
- Ese rastro se ACUMULA vela a vela. La vela 5 no se entiende sin las velas 1–4.
- Los patrones que usamos (fractal de 5 velas, rango de Wyckoff, clímax de
  venta) son formas de LEER ese rastro acumulado, no una vela mágica.

NinjaTrader describe tres huellas que se ven en el rastro de las velas y que
nos sirven en binarias:
- **Imbalance**: una parte aplasta a la otra en un nivel de precio (cuerpo grande
  direccional).
- **Absorption** (absorción): mucho volumen entra y el precio NO se mueve. Es
  decir, unos compran agresivo y otros absorben igual con límites. En velas:
  cuerpos grandes pero el precio no avanza → el rango se está "llenando" (Fase B
  de Wyckoff).
- **Exhaustion** (agotamiento): el volumen se seca en un extremo. La vela se
  achica en el techo/suelo → la fuerza se acabó, viene reversión.

En binarias no tenemos el footprint real (Quotex no da bid/ask por tick), pero el
RASTRO de las velas (cuerpos, mechas, secuencia) es nuestro proxy gratis. Por eso
vale más leer la formación que cazar una vela.
