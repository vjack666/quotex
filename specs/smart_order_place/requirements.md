# Requirements — smart_order_place

> Make order placement **visible and resilient**. Users reported "I hit place order
> and nothing happened" — logs show long waits, `buy_timeout_*`, and broker
> `unexpected` with weak hub feedback.

## R1 — Prewarm trade client
CUANDO el sistema va a sincronizar al open de vela 1m para una entrada, DEBE
precalentar / crear el `trade_client` **antes o durante** la espera (no solo
después del open), de modo que `buy()` se invoque lo antes posible al open.

## R2 — Same-window alt retries
CUANDO la orden del winner falla (timeout, unexpected, connection lost, broker
reject), el sistema DEBE reintentar candidatos alternativos del ranking. Para
cada alt, SI el lag al open actual aún es aceptable, NO debe esperar al próximo
open 1m; SOLO si el lag ya no es válido, espera un único próximo open.

## R3 — Real reject reason
CUANDO un intento de orden falla, el sistema DEBE registrar y exponer el
`reject_reason` real (p.ej. `buy_timeout_60s`, `unexpected`, connection message),
no un hardcode genérico "unexpected" en el log de reintento.

## R4 — last_order_attempt on bot
El sistema DEBE mantener `bot.last_order_attempt` (dict) con al menos:
`asset`, `direction`, `status` (`sending`|`accepted`|`failed`|`waiting_open`),
`reason` (string), `ts` (unix float). Actualizarlo en wait, send, success y fail.

## R5 — Hub exposes attempt
CUANDO el hub serializa estado (`_enrich_with_bot` / `/api/state`), DEBE incluir
`last_order_attempt` desde el bot.

## R6 — Hub UI line
El dashboard DEBE mostrar la última acción de orden de forma legible (texto
corto: esperando open / enviando / aceptada / fallida + asset + reason).

## R7 — Longer quarantine on hard fails
CUANDO el fallo es timeout, connection lost o unexpected, el sistema DEBE
cuarentenar el activo por más ciclos que el default actual de 2
(`ORDER_FAIL_QUARANTINE_CYCLES`, default **5**).

## R8 — STRAT-F untouched
El sistema MUST NOT modificar la lógica de `evaluate_strat_f` / `strat_fractal.py`.

## R9 — Tests
Tests DEBEN cubrir: (a) alt retry path no re-espera open cuando lag OK (mock
time/sync), (b) last_order_attempt se setea en fail/success, (c) hub enrich
incluye el campo. pytest de esos tests MUST pass.
