# 08 — Filtros de calidad: por qué rechazar es ganar

> Fuentes: backtesting multi-timeframe (quantifiedstrategies.com, traderspost.io,
> fxreplay.com), metodología de validación de estrategias. Aplicado a STRAT-F.

## La idea central

En binarias, **cada entrada que evitas mal es dinero que no pierdes**. Una
estrategia buena no es la que más señales da, sino la que **filtra** las malas.
El backtesting multi-timeframe demuestra que exigir alineación entre
temporalidades sube el win rate (ej. estudios reportan 73% con MTF vs. mucho
menos sin alineación), a costa de menos operaciones. Menos, pero mejores.

## Los 6 filtros de STRAT-F

STRAT-F rechaza una señal (y lo registra en el log como
`[STRAT-F] <activo> skip: <razon>`) cuando falla cualquiera de estos:

1. **Payout mínimo (R2)** — si el par paga menos de `STRAT_F_MIN_PAYOUT` (80%),
   no se evalúa. Un win a payout bajo no compensa el riesgo binario.
2. **Contexto M15 roto (existente)** — si el rango Wyckoff de M15 está roto, no
   operamos rebotes: el "suelo" o "techo" ya no existe.
3. **Alineación M15/M5 (R1)** — no se opera un CALL (fractal de suelo M5) si M15
   está en downtrend, ni un PUT si M15 está en uptrend. La mayor manda.
4. **Edad mínima de la banda (R3)** — un fractal recién formado
   (`< STRAT_F_ZONE_MIN_AGE` velas M5) todavía no es una zona validada. Una zona
   necesita que el precio la haya respetado varias velas.
5. **Rechazo M1 (R4)** — la vela M1 debe TOCAR la banda y cerrar del lado
   correcto (no cerrar fuera). Es el principio de Ruben: no basta el nivel, el
   precio tiene que dejar el rastro del rechazo.
6. **Score mínimo (R6)** — la fuerza combinada (`strength * 100`) debe superar
   `STRAT_F_MIN_SCORE` (60). Si el contexto es débil, no vale la pena.

## Por qué NO evaluamos sobre una sola vela

Cada filtro mira una **secuencia** de velas cerradas, no la vela en curso:

- El contexto M15 se lee sobre una ventana de ~12 velas.
- El fractal M5 son 5 velas (2 antes, el pivote, 2 después).
- El rechazo M1 exige que la vela cierre — una mecha fugaz intra-vela no cuenta.

El mercado se forma dejando un rastro (ver libro `formacion_velas/`). Juzgar una
sola vela es leer una palabra de una frase. STRAT-F lee la frase entera.

## Fase A de Wyckoff como refuerzo (no como veto)

Cuando M15 muestra clímax de participación (cuerpo grande + `ticks` altos)
seguido de absorción (cuerpos pequeños, pocos ticks), STRAT-F suma +0.15 a la
fuerza. No es un filtro que rechace: si el par no reporta `ticks` (algunos OTC),
simplemente no aplica el bonus, sin penalizar.

## Validación: cómo saber si los filtros son correctos

- **Backtest**: el backtester reconoce el origen `STRAT-F` y reporta win rate,
  profit y drawdown diferenciados. Si el filtro "rechazo M1" mata demasiado, el
  backtest lo mostrará como pocas entradas con win rate alto → aflojar tolerancia.
- **Demo en vivo**: correr solo STRAT-F en PRACTICE ≥60 min y comparar señales
  emitidas vs. rechazadas. El log documenta cada `skip` con su razón.
