# 6 · Aplicado a binarias (M1 / M5 / M15)

Nuesto marco (ver `wyckoff/` y `fractales/`): M15 mayor, M5 media, M1 menor,
expiración 3 min. Este libro dice CÓMO leer cada temporalidad sin caer en la vela
aislada.

## M15 (contexto, la mayor)
- No buscamos "la vela M15": buscamos el RASTRO de las últimas ~10–12 velas.
- ¿Vino de un clímax y se está absorbiendo (Fase A→B)? ¿Está en rango? ¿Rompio?
- La mayor manda: si el rastro M15 dice "rango roto a la baja", no operamos
  rebotes aunque M1 pinte algo lindo.

## M5 (estructura, la media)
- El fractal de Bill Williams (5 velas) vive aquí. Es una formación, no una vela.
- El evento (fractal en banda naranja) es el RASTRO de que el precio tocó la zona
  y la respetó varias veces.

## M1 (ejecución, la menor — la más tentadora de juzgar sola)
- Es donde operamos (entrada y expiración 3 min = 3 velas M1).
- Peligro máximo: la vela M1 en curso parece "rebote" pero le faltan 40 segundos.
- Correcto: esperar el CIERRE de la vela M1 que rechaza la banda. La mecha es el
  rastro del toque; el cierre es la confirmación de que no cruzó.

## Resumen para el bot
STRAT-F ya hace esto: evalúa con velas CERRADAS de las 3 temporalidades. El
principio de Ruben está codificado en que `evaluate_strat_f` recibe listas de
velas completas, no la última a medias.
