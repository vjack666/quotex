# Requirements — Reemplazo del HUB por panel STRAT-F

> Reemplaza el dashboard actual (orientado a STRAT-A / Masaniello) por uno
> nuevo centrado en la filosofía de STRAT-F: **calidad sobre cantidad**,
> mostrando aceptadas vs rechazadas con la razón de cada rechazo.
> Autorizado sin preguntar (directiva del usuario 2026-07-11).

## Contexto

El `hub/` actual (`server.py`, `hub_scanner.py`, `hub_models.py`, `static/index.html`)
está acoplado a STRAT-A: modelos `CandidateData`/`HubState`/`MasanielloState`,
`record_scan_cycle`/`record_entry`/`update_masaniello_state`, y un index.html que
consume esos campos. STRAT-F (la estrategia que cerramos) no tiene
representación en el hub. El usuario quiere reemplazar TODO el dashboard por uno
que muestre la "manera de trabajar nueva": el bot como portero que dice NO.

## Requisitos funcionales (EARS)

- **R1 — Modelo único STRAT-F**: el hub tendrá un estado `StratFHubState`
  con `accepted: List[StratFRow]`, `rejected: List[StratFReject]`,
  `total_assets`, `filtered_count`, `cycle`, `timestamp`. Se elimina la dependencia
  de `CandidateData`/`HubState`/`MasanielloState` para el panel principal.
- **R2 — Aceptadas**: cada señal que pasa todos los filtros STRAT-F se muestra
  con `asset`, `direction`, `strength`, `payout`, `ctx`, `event`.
- **R3 — Rechazadas con razón**: cada activo filtrado se muestra con `asset`,
  `payout` y `skip_reason` legible (ej. "M1 no rebota", "Rango M15 roto",
  "Zona muy joven", "CALL vs tendencia M15"). Sin razón = bug.
- **R4 — Métrica de calidad**: el panel muestra `total_assets`,
  `aceptadas` y `rechazadas` con porcentaje y barras (verde=ok, rojo=rechazo).
- **R5 — Alimentación en vivo (bot)**: `consolidation_bot.py` / `scanner.py`
  llaman a `hub.record_strat_f(snapshot)` cuando STRAT-F emite señal o rechazo,
  alimentando el panel web en tiempo real. (Hoy el bot NO empuja STRAT-F.)
- **R6 — Alimentación por log (fallback)**: si no hay bot corriendo, el panel
  de terminal lee `progress/diag_strat_f_filters.log` (o `diag_strat_f_live.log`)
  vía `hub.parser.HubLogParser` (ya existe) y muestra lo mismo.
- **R7 — Panel de terminal a color (Rich)**: `hub.render.render_dashboard`
  dibuja con Rich (verde/rojo, barras, tabla) en lugar de ASCII plano.
- **R8 — Panel web (FastAPI+WS)**: `server.py` empuja `StratFHubState`
  serializado por WS; `static/index.html` lo renderiza como panel STRAT-F
  (aceptadas/rechazadas/razón). Se mantiene la gracia de caída: si FastAPI
  no está, `main.py` usa solo el panel de terminal.
- **R9 — Sin I/O de broker en el hub**: el hub no importa pyquotex ni abre
  WebSocket de Quotex; solo consume snapshots ya construidos.
- **R10 — No romper lo existente**: tras el reemplazo, `python -m pytest tests/`
  debe pasar 100% (los tests de hub existentes se reescriben para el nuevo modelo).
- **R11 — Libro en boblioteca**: documentar el dashboard nuevo en
  `boblioteca/` (por qué reemplazar, qué muestra, cómo leerlo).

## Fuera de alcance

- No se modifica la lógica de STRAT-F (ya cerrada). Solo su visualización.
- No se mantiene Masaniello/Gale en el panel (se elimina del hub; si el bot los
  usa en vivo, quedan en `consolidation_bot.py` pero fuera del dashboard).
- No se añade nuevo backtest (ya hecho en `strat_f_quality_validation`).

## Criterios de aceptación

1. `pytest tests/` en verde (incluye tests nuevos del hub STRAT-F).
2. `python -m pytest tests/test_hub_strat_f.py -q` → PASS.
3. El panel de terminal (`main.py --hub-readonly --once`) muestra aceptadas y
   rechazadas con razón, a color.
4. El panel web (`server.py`) sirve el nuevo index.html con el mismo datos.
5. El bot en vivo (si corre) empuja STRAT-F al hub vía `record_strat_f`.
