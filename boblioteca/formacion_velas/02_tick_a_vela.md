# 2 · Del tick a la vela

¿Cómo nace una vela de 1 minuto en Quotex (o cualquier broker)?

1. **El reloj abre la vela** en el minuto 0. El primer trade ejecutado fija el
   **Open**.
2. Durante el minuto, llegan **ticks** (citas/transacciones) continuamente.
   Cada tick tiene un precio. El broker va actualizando:
   - **High** = el precio máximo tocado por cualquier tick.
   - **Low** = el precio mínimo tocado por cualquier tick.
   - **Close** = el precio del ÚLTIMO tick antes de cerrar la vela.
3. Al cumplirse el minuto, la vela se "cierra" y se congela. Esa es la foto OHLC.

Puntos clave (reales, no opinión):
- **High/Low se alcanzan en un solo tick** a veces. Una mecha puede ser un tick
  fugaz (una orden grande atravesó) o una zona donde el precio estuvo varios
  segundos. El OHLC no distingue eso.
- El **cuerpo** (Open→Close) es lo que importa para dirección; las mechas son
  los "extremos visitados y rechazados".
- En binarias el **Close es sagrado**: la opción paga según si Close quedó arriba
  o abajo del strike. Por eso operamos sobre el CIERRE, no sobre la mecha.

Esto explica por qué "leer una vela suelta" es peligroso: estamos viendo el
resultado de un proceso de 60 segundos comprimido en 4 números. El proceso (el
order flow) es lo que cuenta.
