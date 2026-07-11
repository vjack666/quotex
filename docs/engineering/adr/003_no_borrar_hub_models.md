# ADR-003 — No borrar `hub_models.py` al reemplazar el dashboard

- **Estado:** Aceptado
- **Fecha:** 2026-07-11

## Contexto

El dashboard viejo (`hub_models.py`, `hub_scanner.py`, `server.py`,
`index.html`) estaba acoplado a STRAT-A / Masaniello. Al reemplazar el panel
por uno STRAT-F, la tentación fue borrar todo lo viejo. En el commit `340597f`
ya se borró a lo loco (`_progress.py`, `regime.py`, `trend_context.py`) y se
rompieron 21/40 tests.

## Decisión

El nuevo panel STRAT-F (`hub/strat_f_state.py`, `hub/strat_f_panel.py`,
`hub/parser.py`, `hub/render.py`) **convive** con el viejo. `hub_models.py` y
el `HubScanner` viejo SE MANTIENEN porque `server.py` y `vip_library.py` los
importan. El bot (`consolidation_bot.py`) sigue alimentando Masaniello vía el
`HubScanner` viejo; STRAT-F se sirve como estado adicional (`strat_f`) en el
mismo servidor.

## Consecuencias

- ✅ No se rompe el bot ni la gestión Masaniello.
- ✅ El panel visible para el usuario es STRAT-F (lo que quería).
- ⚠️ Hay código "muerto" (el render viejo de STRAT-A) que el usuario no ve;
  se puede limpiar en una fase posterior, de a uno en uno, con tests verdes.
- ⚠️ Regla dura del repo (AGENTS.md): mover a `legacy/` con `git mv`, NUNCA
  borrar a lo loco.
