# 02 — Cuándo usarlo (y cuándo NO)

## Regla de oro del libro

El estocástico es un indicador de **rango/lateral**. Brilla cuando el precio
está yendo de un lado a otro dentro de un canal. Falla cuando hay tendencia
fuerte y clara. No es opinión: es lo que dicen Lane y todos los manuales
(StockCharts, Investopedia).

## Cuándo SÍ usarlo

1. **Mercado en rango (consolidación).** El precio rebota entre soporte y
   resistencia. El estocástico te avisa cuándo está "congelado" abajo (<=20)
   cerca del soporte → posible rebote arriba; o "quemado" arriba (>=80) cerca
   de la resistencia → posible caída.
2. **Confirmar un rebote en zona.** Justo lo que hace STRAT-F: si el fractal M5
   toca la banda naranja y el estocástico M15 está en extremo (sobreventa para
   CALL, sobrecompra para PUT), el rebote tiene más probabilidad.
3. **Filtrar señales falsas de continuación.** En rango, una vela que "rompe"
   suele ser fake-out. El estocástico en extremo te frena de entrar a favor del
   fake-out.

## Cuándo NO usarlo solo

1. **Tendencia fuerte.** El estocástico puede quedar EN 80+ durante una suba
   violenta (sobrecomprado pero sigue subiendo), o EN 20- durante una bajada
   fea. Si operás "vendé porque está en 80" en una tendencia alcista fuerte,
   te comés todos los whipsaws. StockCharts lo muestra claro: *"overbought
   readings aren't necessarily bearish... securities can become overbought and
   remain overbought during a strong uptrend."*
2. **Como única razón de entrada.** Nunca. Siempre con otra herramienta:
   soporte/resistencia, volumen, estructura de velas, o en nuestro caso el
   fractal + zona Wyckoff de STRAT-F.

## Los umbrales (los números que el bot lee)

- **>= 80** → sobrecomprado (podría ceder / corregir).
- **<= 20** → sobrevendido (podría rebotar).
- **50** → la línea central, la "línea de 50 yardas". Por arriba del 50 el
  cierre está en la mitad superior de su rango (sesgo alcista del rango); por
  debajo, mitad inferior (sesgo bajista del rango).

Importante: el cruce por 50 confirma sesgo. Un rebote sobrevendido que no
puede volver por arriba de 50 es débil. Una caída sobrecomprada que no baja
de 50 es débil también.

## Ajuste de sensibilidad (esto cambia todo)

- Mira **corta (10)** → oscilador picante, muchas lecturas 80/20, más señales
  y más ruido. StockCharts usa (10,3,3) en una acción en tendencia bajista
  para pescar sobrecompras de rebote.
- Mira **larga (20)** → más suave, menos señales, mejor para rangos limpios.
  Ejemplo real: Full (20,5,5) en un rango $14–$18 durante meses: cada bajada
  bajo 20 avisaba rebote, cada suba sobre 80 avisaba caída.

Para STRAT-F en M15: arrancamos con **(14,3,3)** y lo medimos contra los datos
reales de la caja negra antes de afinarlo.

## La advertencia que el libro repite

> "Como todos los indicadores técnicos, usá el estocástico JUNTO con otras
> herramientas de análisis. Volumen, soporte/resistencia y quiebres pueden
> confirmar o refutar las señales." — StockCharts

Esa es la filosofía de STRAT-F también: el estocástico es UN filtro más, no el
jefe. Por eso lo vamos a grabar en la caja negra y decidir con datos, no por fe.

---
Fuentes: StockCharts ChartSchool, Investopedia.
