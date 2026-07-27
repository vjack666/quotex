# Design — Observador Fase B: Calidad del Rebote y Película Completa

Trazabilidad: referencias R<n> a requirements.md.

## Paquete (extiende `src/observador/`, no crea nuevo)

```
src/observador/
  config/                      # <-- NUEVO: parámetros VERSIONADOS, NO en SDD
    evolution_v1.yaml          # umbrales CaptureMonitor, vars por activo
  metric.py        (Fase A)   # Metric reusado
  pressure.py      (Fase A)   # reusado
  state_machine.py (Fase A)   # reusado; emite estados estructurales
  store.py         (Fase A)   # EXTENDIDO: nuevas tablas, idempotencia intacta
  evolution.py     # NUEVO: EpisodeEvolutionWriter + CaptureMonitor
  summary.py       # NUEVO: EpisodeSummary (snapshot final)
  observer.py      (Fase A)   # MODIFICADO: orquesta writer tras RESOLUTION
  config_loader.py # NUEVO: carga cfg versionada por activo
```

## Principio: comportamiento, no parámetros (D0)
Todo número vive en `config/evolution_v1.yaml` (versionado con git). El código
lee el cfg; el SDD no nombra ningún literal. Cambiar un umbral = editar yaml +
bump de version, sin tocar arquitectura.

## Store (D1, R2/R8/R11) — SQLite WAL, esquema aditivo
Nuevas tablas; las de Fase A se conservan.

```sql
-- traza barra a barra (R1/R2/R3)
CREATE TABLE episode_evolution (
  episode_id   INTEGER,
  bar_index    INTEGER,           -- 0,1,2… relativo al inicio (R1)
  ts           REAL,
  price        REAL,
  distance_pips REAL,             -- vs origen del episodio
  mfe          REAL,              -- max a favor acumulado
  mae          REAL,              -- max en contra acumulado
  state        TEXT,              -- estado estructural en la barra
  vars_json    TEXT,              -- {"continuity":..,"energy":..,"vol":..} (R3)
  vars_version TEXT,              -- formula_version del bloque de vars
  PRIMARY KEY (episode_id, bar_index)
);

-- resumen para IA (R8/R10)
CREATE TABLE episode_summary (
  episode_id      INTEGER PRIMARY KEY,
  quality         REAL,  velocity TEXT, violence TEXT,
  curve_shape     TEXT,  symmetry REAL,
  episode_type    TEXT,  duration_bars INTEGER,
  mfe             REAL,  mae REAL,
  end_reason      TEXT,  end_confidence REAL,
  finished        INTEGER,         -- 1 natural, 0 fin-de-captura (R4/R5)
  capture_limit   INTEGER          -- 1 si paró por CaptureMonitor (R5)
);

-- versión de fórmulas por episodio (R10)
CREATE TABLE episode_version (
  episode_id INTEGER PRIMARY KEY,
  vars_version TEXT, summary_version TEXT
);
```
Idempotencia (R11): clave natural heredada `(asset,ts_open,source)`; en
backfill se upsert episode_evolution por `(episode_id,bar_index)` y se
reemplaza episode_summary.

## EpisodeEvolutionWriter (D2, R1/R2/R3/R12)
- Se instancia por episodio activo. Recibe cada vela M1 desde el inicio del
  episodio (no solo tras RESOLUTION).
- `record(bar_index, candle, state, vars)` escribe fila con distance/mfe/mae
  vivos. `mfe`/`mae` se llevan acumulados vs el punto de entrada. NUNCA usa
  reloj de pared (R12) — `bar_index` y `ts` vienen del evento.
- Variables `vars` (R3): dict de las definidas en cfg; cada una con su
  `formula_version` (R10). Fórmulas residen en `summary.py`/`metrics`,
  versionadas.

## CaptureMonitor (D3, R5/R6/R7)
Por barra evalúa dimensiones configurables:
`hubo_cambio_estructural?`, `cambió_presión?`, `cambió_energía?`,
`cambió_dirección?`, `cambió_volatilidad?`. Termina captura SOLO cuando TODAS
= sin cambio (R6). Cada dimensión usa umbrales POR ACTIVO del cfg (R7). No usa
conteo fijo de barras (R5/R6). Devuelve `CAPTURE_FINISHED` con
`capture_limit_reached=true`, sin alterar `finished` natural.

## Fin natural vs fin de captura (D4, R4/R5)
- Fin NATURAL: la máquina de estados emite un estado de cierre real
  (NEW_EXPANSION / NEW_PRESSURE / OPPOSITE_STRUCTURE / CHAOS). El writer
  cierra con `finished=1`, `end_reason=<estado>`, `end_confidence=<del trigger>`.
- Fin DE CAPTURA: CaptureMonitor dice parar; el episodio sigue sin resolución
  natural. `finished=0`, `capture_limit_reached=1`, `end_reason=NULL`.
- Diferencia semántica preservada explícitamente: el Atlas nunca confunde
  "el mercado terminó" con "dejamos de observar".

## EpisodeSummary (D5, R8/R10)
Al cerrar (natural o captura), `summary.py` computa el snapshot:
- `quality`: heurística versionada (ej. mfe/(mfe+|mae|) ponderada por simetría)
  — fórmula en cfg/summary_v1, recalculable.
- `velocity` (rápido/lento), `violence` (alta/baja): buckets versionados.
- `curve_shape`: compara MFE vs recorrido neto → convexa/cóncava/plana.
- `symmetry`: correlación de la curva ida/vuelta, versionada.
- `episode_type`: Reversal/Continuation/Chaos (hereda `resolution_type`).
- `duration_bars`, `mfe`, `mae`, `end_reason`, `end_confidence`, `finished`.

## Observer modificado (D6, R9/R11/R12)
- Tras `RESOLUTION` (Fase A) el loop NO reinicia la máquina de inmediato:
  sigue alimentando el EpisodeEvolutionWriter con velas M1 hasta que
  CaptureMonitor dispara (R5) o sobreviene fin natural (R4). El writer es
  independiente de `resolution_type`.
- 100% agnóstico a vehículo de negocio (R9): el observer no sabe de binarias.
- Re-correr 14 años = backfill idempotente (R11): episodios preexistentes se
  completan con traza+resumen, sin duplicar.

## Config versionada (D0, R3/R5/R7/R10)
`config/evolution_v1.yaml`:
```yaml
version: evolution_v1
vars: [continuity, pressure, energy, volatility, spread]   # R3
capture:                                                   # R5/R6/R7
  dimensions: [structural, pressure, energy, direction, volatility]
  per_asset:
    EURUSD:   {silence_meaning: ..., flat_range: <cfg>, ...}  # sin literales en SDD
    XAUUSD:   {...}
summary:                                                   # R8/R10
  quality_formula: v1
  ... 
```
Los nombres de campos son de diseño; los VALORES son parámetros
experimentales validados por el Atlas. Bump de `version` al cambiar fórmulas.

## Candados (D7, R12/R13)
- `tests/test_observador_no_wallclock.py` (Fase A) ya vigila `src/observador/`
  completo → cubre Fase B sin modificar. R12 satisfecho por herencia.
- Grep de candado anti-bot (R13) reusado en T-final.

## Trazabilidad requirements↔design
R1→D1/D2 · R2→D1/D2 · R3→D0/D2/D3config · R4→D4 · R5→D3/D4 · R6→D3 ·
R7→D0/D3config · R8→D1/D5 · R9→D6 · R10→D0/D1/D5 · R11→D1/D6 · R12→D2/D6/D7 ·
R13→D7
