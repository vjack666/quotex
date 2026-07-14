# 01 — Historia y qué es el Estocástico

## La historia completa (no es humo, es documentado)

El estocástico lo inventó **George C. Lane** a fines de la década del **1950**.
Lane fue uno de los pioneros del análisis técnico moderno. Su gran observación
no fue sobre el precio en sí, sino sobre la **velocidad del precio**.

Su analogía famosa: *"Igual que una pelota que tirás para arriba se frena
antes de invertir y volver a bajar, el momentum de un activo cambia de dirección
ANTES que el precio."* Esa es la piedra angular del indicador: **el momentum
cambia primero, el precio lo sigue.**

Por eso el estocástico **no sigue al precio, ni al volumen**. Sigue la
velocidad (momentum) del precio. Cuando el momentum da vuelta, el precio suele
hacerlo poco después. Lane decía que la **divergencia** era la SEÑAL #1 del
indicador — la única que, según él, te hace comprar o vender con razón.

Con el tiempo el indicador evolucionó en tres versiones (rápida, lenta, full),
cada una con distinta sensibilidad. Hoy es una herramienta central del análisis
técnico, al nivel del RSI y el MACD.

## Qué mide (en criollo)

El estocástico es un **oscilador de momentum** que compara el precio de cierre
actual contra el rango alto-bajo de un período. Te dice: *"¿dónde cerró este
activo DENTRO de su rango reciente? ¿Cerca del techo, cerca del piso, o al medio?"*

Está acotado entre **0 y 100** siempre. Por eso se llama oscilador de banda:
no importa qué tan fuerte suba o baje el activo, el estocástico siempre vive
entre 0 y 100.

- Cerca de **100** → el cierre está pegado al máximo del rango (el activo "quema").
- Cerca de **0** → el cierre está pegado al mínimo del rango (el activo "se congela").
- Cerca de **50** → el cierre está en la mitad del rango.

## La fórmula (esto es lo que el bot va a calcular)

```
%K = (Cierra - MínimoLow) / (MáximoHigh - MínimoLow) * 100

%D = promedio móvil simple de 3 períodos de %K
```

Donde:
- `Cierra` = precio de cierre actual.
- `MínimoLow` = el mínimo más bajo de las últimas N velas.
- `MáximoHigh` = el máximo más alto de las últimas N velas.
- `%K` = la línea rápida (posición del cierre en el rango).
- `%D` = la línea lenta (suavizado de %K, actúa como línea de señal/disparo).

Ejemplo concreto (StockCharts): si el máximo es 110, el mínimo es 100, y el
cierre es 108 → rango = 10, numerador = 8 → %K = 80. Si el cierre fuera 103
→ %K = 30.

Configuración por defecto: **(14, 3)**. 14 velas de mira, %D = media de 3.
Para binarias en M15 vos usás (14, 3) o (14, 3, 3) full.

## Tres versiones (para saber de qué hablan)

- **Rápido (Fast)**: %K original, %D = SMA 3 de %K. Más ruido, más whipsaws.
- **Lento (Slow)**: %K suavizado con SMA 3 (queda igual a %D del rápido), %D = SMA 3. Más limpio.
- **Full (14,3,3)**: vos elegís mira, suavizado de %K y suavizado de %D. El más flexible.

Para STRAT-F vamos a usar el **Slow/Full (14,3,3)** en M15: suficiente
suavizado para no disparar por ruido, y la mira de 14 velas da contexto de
rango real.

## Por qué importa para nosotros

STRAT-F opera **rebotes en bandas naranjas (zonas Wyckoff)**. El estocástico
en M15 es justo un medidor de "¿está el precio en un extremo de su rango
(recalentado o congelado) y listo para rebotar?". Eso es exactamente el
contexto que le falta a STRAT-F para no entrar CALL cuando el M15 ya está
en sobrecompra extrema (falsa continuación). Lo desarrollamos en el archivo 04.

---
Fuentes: StockCharts ChartSchool (documentación canónica de Lane), Investopedia.
