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
| Tests actuales | 246 passing |

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

---

## Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-07-11 | Borrado de `feature_list.json` viejo y `docs/ROADMAP*.md` (mintieron sobre strat_b) |
| 2026-07-11 | Creación de roadmap STRAT-F (feature #1 en curso) |
| 2026-07-11 | Reemplazo del dashboard por panel STRAT-F (#7): `hub/strat_f_state.py`, `hub/strat_f_panel.py`, `hub/parser.py`, `hub/render.py`, `hub/server.py` + `index.html` reescrito |
