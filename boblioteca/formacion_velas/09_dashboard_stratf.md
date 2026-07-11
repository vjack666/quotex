# 09 — El dashboard STRAT-F: ver al portero en acción

> Por qué reemplazamos el panel viejo (STRAT-A / Masaniello) por uno que
> solo muestra la calidad de STRAT-F: aceptadas vs rechazadas con razón.

## El problema del dashboard viejo

El panel anterior estaba atado a STRAT-A: mostraba candidatos de
consolidación, el estado de Masaniello (5 ops / 3 ITM / 60 min) y el
Gale. Eso es la *gestión del dinero*, no la *calidad de la señal*.

Pero lo que Ruben quiere ver es otra cosa: **cómo el bot decide NO
operar**. El principio de hierro de las binarias acá es: nunca evaluar
una señal en una sola vela; el mercado deja rastro. El dashboard tiene
que mostrar ese rastro y, sobre todo, por qué se descartó cada activo.

## Qué muestra el nuevo panel

Un solo estado `StratFHubState`:

- **Aceptadas** — señales que pasaron TODOS los filtros:
  activo, dirección (CALL/PUT), fuerza, payout, contexto M15, evento M5.
- **Rechazadas** — cada activo descartado con su `skip_reason` legible:
  - `M1 no rebota (cierre fuera)` — tocó la banda pero la vela cerró del
    lado equivocado. Tu principio: la pelota tiene que volver.
  - `Rango M15 roto` — el rango Wyckoff se rompió; no hay suelo/techo
    donde rebotar. Como esperar rebote en una pared que cayó.
  - `Zona muy joven` — la banda tiene menos de 3 velas M5; no está
    validada. No te fías de un puente recién pintado.
  - `CALL/PUT vs tendencia M15` — la temporalidad mayor manda; no operás
    contra ella (escalera mecánica que baja).
- **Métrica de calidad** — total de activos, aceptadas y rechazadas con
  porcentaje y barras (verde=ok, rojo=rechazo).

## Cómo leerlo

Si ves 1 aceptada y 13 rechazadas (como en la corrida de hoy), **está
bien**. Eso es el bot siendo selectivo. Cada rechazo es plata que no
perdiste. El panel no es "cuántas operó" sino "cuántas malas evitó".

Si un día ves 0 aceptadas, el mercado no dio nada bueno: el bot se quedó
quieto. Esa es la ventaja de STRAT-F sobre operar a ciegas.

## Dónde vive y cómo correrlo

- `hub/strat_f_state.py` — el modelo (la única fuente de verdad).
- `hub/parser.py` — lee el log del diag `diag_strat_f_live.py`.
- `hub/render.py` — dibuja el panel (Rich si está, texto plano si no).
- `hub/strat_f_panel.py` — capa visible que el bot alimenta en vivo.
- `hub/server.py` — web: empuja `strat_f` por WebSocket + `/api/strat_f`.
- `hub/static/index.html` — panel web (aceptadas verdes / rechazadas rojas).

Para verlo en terminal:
  .\.venv\Scripts\python.exe progress\diag_strat_f_live.py
  .\.venv\Scripts\python.exe main.py --hub-readonly --once

Para verlo en web (si el bot corre): abrí `http://localhost:8000`.

## Decisión de diseño: Rich

Elegimos Rich (estándar de dashboards de terminal en Python) para color
semántico: verde=aceptada, rojo=rechazada. Refuerza el principio sin
leer código. Si Rich no está en el venv, el panel cae a texto plano
(import opcional) — nunca se rompe.

## Lección de ingeniería (para no romper el bot)

El hub viejo alimentaba a Masaniello. En lugar de borrarlo a lo loco
(lección del commit 340597f que rompió 21/40 tests), el nuevo panel
**convive**: el bot sigue usando Masaniello internamente, pero el panel
visible es STRAT-F. `hub_models.py` se mantuvo intacto. Reemplazar la
*vista* no significa reescribir la *lógica*.
