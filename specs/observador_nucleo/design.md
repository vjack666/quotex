# Design — Observador Fase A: Núcleo de Episodios

Trazabilidad: referencias R<n> a requirements.md.

## Paquete

`src/observador/` (nuevo, independiente del bot vivo — R5.1):
- `metric.py`    — dataclass Metric{raw, normalized, confidence, formula_version} (PTM v3).
- `state_machine.py` — EpisodeStateMachine: estados y reglas de transición v1.
- `pressure.py`  — cálculo del punto de PressureCurve por vela M1 (R3.1).
- `observer.py`  — Observador: loop consume feed → alimenta máquinas por asset.
- `store.py`     — EpisodeStore SQLite (WAL, idempotente, schema_version).

## Decisiones

D1 (R1.1) El Observador recibe `feed: MarketFeed` inyectado. Único reloj:
`feed.now()`. Test A3 lo vigila por grep + revisión.

D2 (R2.2) Definición v1 de "salir de lo aburrido" (formula_version
`quiet_exit_v1`): sobre ventana móvil de 30 velas M1, si |close-open| de la
vela actual > 2.0 × mediana de los cuerpos de la ventana Y hay ≥3 velas
consecutivas en la misma dirección → EXPANSION. Umbrales en constantes
versionadas, no mágicos sueltos (PTM v3).

D3 (R2.x) Transiciones v1 (todas versionadas `transitions_v1`):
- EXPANSION→PRESSURE: la dirección se sostiene (continuidad ≥ 0.7 en 5 velas).
- PRESSURE→BRAKE: avance neto por vela cae < 30% del pico del episodio
  durante ≥2 velas (el freno de la Constitución, Ley 2).
- BRAKE→TRANSITION: primera vela de cierre contrario a la dirección del episodio.
- TRANSITION→RESOLUTION: 5 velas después de TRANSITION se clasifica:
  avance contrario ≥ 2×cuerpo mediano → REBOUND; retomó dirección → CONTINUATION;
  alternancia sin dirección → CHAOS. Timeouts (R2.4): 60 velas por estado →
  NEUTRALIZATION. Heurísticas simples A PROPÓSITO: Fase A captura el esqueleto;
  la riqueza llega en Fase B con evidencia del Atlas.

D4 (R4) SQLite en data/observador/episodes.db:
- meta(schema_version, created_ts)
- episodes(id, asset, source, ts_open, ts_close, state_final, resolution_type,
  formula_version, confidence, UNIQUE(asset, ts_open, source))
- episode_states(episode_id, state, ts_enter, trigger_raw, trigger_norm,
  trigger_confidence, trigger_formula)
- pressure_points(episode_id, ts, direction, net_advance_raw, net_advance_norm,
  continuity, confidence, formula_version)
UPSERT por clave natural (R4.3) → idempotencia por construcción.

D5 (R1.3) FEED_GAP: baja confidence del episodio activo (×0.5, acumulativo,
mín 0.1) y se anota en episode_states como evento GAP. No cierra el episodio.

D6 Multi-asset: dict asset→state machine; eventos llegan mezclados del merge
del ReplayFeed y cada máquina solo ve su asset. Sin threads: síncrono como el feed.

## Alternativas descartadas
- Detectar QUIET-exit con desviación estándar: más sensible a outliers que la
  mediana; la mediana ya probó robustez en la anticontaminación del replay.
- Persistir en el mismo DB de la caja negra: mezcla capas (R5.1) — DB propio.
- Async/colas: innecesario, el feed es síncrono y determinista.

## Estrategia de test
Unit por módulo (máquina con secuencias sintéticas de velas que fuerzan cada
transición), store (idempotencia, WAL), pressure (aritmética a mano), y los
5 criterios A1-A5 como tests de integración. Fixtures sintéticas; E2E usa
ParquetSource real solo si el archivo existe (skipif).
