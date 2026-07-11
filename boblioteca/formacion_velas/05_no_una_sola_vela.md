# 5 · Nunca una sola vela (el principio de Ruben)

> "En binarias no quiero que todo se evalúe en una sola vela. El mercado se va
> formando y a su vez deja un rastro."

Esto tiene tres consecuencias operativas que ya aplicamos en el bot:

## 1) La vela en curso no se juzga
Mientras la vela de M1 está abierta, su High/Low/Close se mueven cada tick.
Cualquier decisión tomada "ahora" sobre ella es sobre una foto a medio hacer.
Por eso STRAT-F (y STRAT-A) espera **señales sobre velas cerradas**, no sobre la
que está corriendo. El cierre es el único dato estable.

## 2) Se lee la formación, no el clímax
Un fractal de Bill Williams son 5 velas: la del medio es el giro, pero solo
"cuenta" porque las 2 a cada lado la respaldan. Un rango de Wyckoff son decenas
de velas laterales. Un clímax de venta (Fase A) es UNA vela grande SEGUIDA de
velas de absorción. Ninguno existe "en una vela".

## 3) El rastro de las previas es el filtro
La vela actual solo opera si las anteriores dejaron el rastro correcto:
- STRAT-F: M15 debe mostrar contexto (range/broken, no tendencia que aplasta),
  M5 debe mostrar el fractal en una banda, y recién ahí el M1 rechaza.
- Eso son 3 temporalidades LEYENDO el rastro de cada una. Nunca "la vela M1 dice
  CALL".

Regla de oro del libro: **la vela suelta es ruido; la formación + el rastro son
señal.**
