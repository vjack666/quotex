# Tasks — Reemplazo del HUB por panel STRAT-F

> Ejecución TDD, una feature a la vez, pytest verde antes de declarar hecho.

- [x] T1 — Crear `hub/strat_f_state.py` con `StratFRow`, `StratFReject`, `StratFHubState`. Cubre: R1.
- [x] T2 — Test `tests/test_hub_strat_f.py`: construir `StratFHubState`. Cubre: R1, R10.
- [x] T3 — Test parser: `HubLogParser` parsea log del diag a `StratFHubState`. Cubre: R6, R10.
- [x] T4 — `hub/render.py` usa Rich (fallback plano). Cubre: R4, R7.
- [x] T5 — Test render: panel contiene secciones + datos. Cubre: R2, R3, R10.
- [x] T6 — `hub/strat_f_panel.py` con `record_strat_f` + `get_state()`. Cubre: R1, R5.
- [x] T7 — `hub/__init__.py`: exports actualizados. Cubre: R1.
- [x] T8 — Test `record_strat_f` acumula accepted/rejected. Cubre: R5, R10.
- [x] T9 — `_render_hub_once` en `main.py` usa `hub.render` + parser. Cubre: R6, R7.
- [x] T10 — `server.py` `_build_snapshot` incluye `strat_f`. Cubre: R8.
- [x] T11 — Reescribir `hub/static/index.html` panel STRAT-F vía WS. Cubre: R8.
- [x] T12 — Endpoint `/api/strat_f`. Cubre: R8, R9, R10.
- [x] T13 — `scanner.py` acumula `_strat_f_batch` y llama `record_strat_f`. Cubre: R5.
- [x] T14 — `consolidation_bot.py`: se mantiene Masaniello (no roto); HUB STRAT-F additive. Cubre: R5, riesgo R3.
- [x] T15 — Test integración: scanner construye snapshot y lo pasa al panel. Cubre: R5, R10.
- [x] T16 — `hub_models.py` SE MANTIENE (riesgo R1 evitado: server.py sigue usándolo; Masaniello vive en el bot). Cubre: R1.
- [x] T17 — `index.html` viejo reemplazado (T11).
- [x] T18 — `pytest tests/` → 273 verde. Cubre: R10.
- [x] T19 — `boblioteca/formacion_velas/09_dashboard_stratf.md`. Cubre: R11.
- [x] T20 — `feature_list.json` (#7) + `docs/ROADMAP.md` → done.
- [x] T21 — `pytest tests/` final → 273 passed. Cierre SDD.
