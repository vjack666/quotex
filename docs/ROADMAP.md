# Roadmap — quotex-hft-bot (post-Strategy B)

> **Fuente de verdad:** `feature_list.json`
> **Última actualización:** 2026-07-11
> **Contexto:** Strategy B (Wyckoff Spring) fue eliminada físicamente. El bot
> ahora se enfoca en una estrategia unificada **STRAT-F (Fractal / Wyckoff)**
> basada en los libros de `boblioteca/`.

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Estrategias vivas | STRAT-A, MOMENTUM, REVERSAL_SWING, ORDER_BLOCK |
| Nueva estrategia en construcción | **STRAT-F** (fractal M15/M5/M1) |
| Strategy B | **ELIMINADA** (2026-07-11) |
| Gestión de riesgo | Massaniello (5 ops / 3 ITM / 60 min / PRACTICE) |
| Tests actuales | 286 passing |

---

## Concepto de STRAT-F (une los libros de `boblioteca/`)

Marco fractal (la temporalidad mayor manda):
- **M15 (mayor / contexto)**: ¿el par está en rango Wyckoff o en tendencia?
  Si el rango está roto, no operamos rebotes.
- **M5 (media / estructura)**: fractal Bill Williams de 5 velas que cae en una
  banda naranja (zona Wyckoff) = evento de entrada.
- **M1 (menor / ejecución)**: vela que toca la banda y la rechaza (no cierra fuera).

Expiración 3 min (3 velas de M1). Alineación M15+M5+M1 sube la probabilidad.

---

## Roadmap por fases

### Fase 0 — Acomodar el scanner (base de STRAT-F)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 1 | `scanner_multi_tf_prefetch` | ✅ done | — |

### Fase 1 — STRAT-F (nueva estrategia)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 2 | `strat_f_baseline` | ✅ done | #1 |
| 3 | `strat_f_scanner_wiring` | ✅ done | #2 |
| 4 | `strat_f_filters` | ✅ done | #3 |

### Fase 2 — Validación
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 5 | `strat_f_backtest` | ✅ done | #3 |
| 6 | `strat_f_live_validation` | ✅ done | #4, #5 |

> **STRAT-F cerrado** (2026-07-11). SDD: `specs/strat_f_quality_validation/`.
> pytest 267 passed. Próxima fase a definir.

### Fase 3 — Dashboard STRAT-F (reemplazo del panel viejo)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 7 | `hub_strat_f_replacement` | ✅ done | #1, #2, #3, #4, #5, #6 |

> **Dashboard reemplazado** (2026-07-11). SDD: `specs/hub_strat_f_replacement/`.
> El panel ahora muestra aceptadas vs rechazadas STRAT-F con razón. pytest 273 passed.

---

## Módulos afectados por STRAT-F

| Módulo | Cambio |
|--------|--------|
| `scan_prefetch.py` | bajar 15m → `ScanCycleData.candles_15m` (#1) |
| `src/strat_fractal.py` | **NUEVO** evaluador puro STRAT-F (#2) |
| `scanner.py` | cablear bloque STRAT-F (#3) |
| `config.py` | constantes `STRAT_F_*` (#3/#4) |
| `backtester.py` | reconocer origen `STRAT-F` (#5) |
| `tests/test_strat_fractal.py` | **NUEVO** (#2) |
| `hub/strat_f_state.py` | **NUEVO** modelo `StratFHubState` (#7) |
| `hub/strat_f_panel.py` | **NUEVO** capa visible STRAT-F (#7) |
| `hub/parser.py` | parsea log del diag a `StratFHubState` (#7) |
| `hub/render.py` | panel a color (Rich) aceptadas/rechazadas (#7) |
| `hub/server.py` | empuja `strat_f` por WS + `/api/strat_f` (#7) |
| `hub/static/index.html` | **REESCRITO** a panel STRAT-F (#7) |
| `scanner.py` | acumula `record_strat_f` y lo empuja al HUB (#7) |

### Fase 4 — Documentación de ingeniería (SRS/ADR/ERD/API/ATDD)
| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 8 | `engineering_docs` | ✅ done | #1–#7 |

> **Documentación de ingeniería completa** (2026-07-11). En `docs/engineering/`:
> `SRS.md` (objetivo 5 entradas/2h + NFR), `adr/` (3 ADR: evaluador puro,
> SQLite diario, no borrar hub_models), `erd_trade_journal.md`, `api_spec.md`,
> `glosario.md`. Test ATDD `tests/test_window_2h.py` fija el contrato de
> volumen (N1). pytest **282 passed**.

---

## Módulos de documentación (Fase 4)

| Archivo | Contenido |
|---------|-----------|
| `docs/engineering/SRS.md` | Requisitos funcionales (F1–F12) y no funcionales (N1–N9) |
| `docs/engineering/adr/001_evaluador_puro.md` | STRAT-F como evaluador puro (no opera) |
| `docs/engineering/adr/002_sqlite_diario.md` | Diario en SQLite local |
| `docs/engineering/adr/003_no_borrar_hub_models.md` | No borrar hub_models al reemplazar dashboard |
| `docs/engineering/adr/README.md` | Índice de ADR |
| `docs/engineering/erd_trade_journal.md` | Diagrama de tablas del diario |
| `docs/engineering/api_spec.md` | Contrato de hub/server.py (/api/state, /api/strat_f, /ws) |
| `docs/engineering/glosario.md` | Acrónimos SRS/FRS/NFR, SDD/SAD, ADR/RFC, TDD/BDD/ATDD, MCP/RAG/DSPy... |
| `tests/test_window_2h.py` | ATDD: ventana 2h produce >= 5 entradas STRAT-F |

---

## Fase 5 — Go-Live STRAT-F (GAPs G1+G2 de la auditoría)

| ID | Feature | Estado | Depende de |
|----|---------|--------|------------|
| 9 | `strat_f_panel_live` (G1) | ✅ done | #7 |
| 10 | `strat_f_only_mode` (G2) | ✅ done | #4, #9 |

> **G1+G2 cerrados** (2026-07-11). El panel STRAT-F se muestra en el bot REAL
> (no solo `--hub-readonly`) y `STRAT_F_ONLY=True` aisla la ejecución a STRAT-F
> para garantizar el 1er trade demo. `tests/test_strat_f_golive.py` (4 tests,
> TDD). pytest **286 passed**. Auditoría: `progress/audit_strat_f_go_live.md`.
> **G3 (end-to-end en máquina de Ruben) PENDIENTE**: falta correr `main.py` en
> demo y confirmar panel + 1er trade cerrado.

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-07-11 | Borrado de `feature_list.json` viejo y `docs/ROADMAP*.md` (mintieron sobre strat_b) |
| 2026-07-11 | Creación de roadmap STRAT-F (feature #1 en curso) |
| 2026-07-11 | Reemplazo del dashboard por panel STRAT-F (#7): `hub/strat_f_state.py`, `hub/strat_f_panel.py`, `hub/parser.py`, `hub/render.py`, `hub/server.py` + `index.html` reescrito |
| 2026-07-11 | Documentación de ingeniería (#8): `docs/engineering/` (SRS, 3 ADR, ERD, API Spec, glosario) + `tests/test_window_2h.py` (ATDD ventana 2h). pytest 282 passed |
| 2026-07-11 | **Go-Live GAPs G1+G2 cerrados**: panel STRAT-F cableado al bot real (`_flush_strat_f_panel` en `scan_all` + `StratFPanel` en `ConsolidationBot` + `server.init` lo usa por WS) y modo `STRAT_F_ONLY` que aísla la ejecución STRAT-F. `tests/test_strat_f_golive.py` (4 tests). pytest **286 passed**. Falta G3 (end-to-end en máquina de Ruben). |
