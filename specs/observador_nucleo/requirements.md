# Requirements — Observador Fase A: Núcleo de Episodios (PTM v3)

Feature: observador_nucleo
Capa: 2 (Observador). Consume la Capa 0.5 (MarketFeed). NO decide, NO opera.
Documentos rectores: docs/FILOSOFIA.md (P3: el Observador nunca decide),
docs/PTM_V3.md (CONGELADO — este spec lo implementa, no lo reinterpreta),
docs/CONSTITUCION_REBOTE.md, docs/REPLAY_ENGINE.md.

Alcance Fase A: máquina de estados del episodio + PressureCurve + persistencia.
FUERA de alcance (Fases B/C): Participants, Expectations, Timing/instrument_readings,
Resolution rica (MFE/MAE), Narrative, export Atlas.

## R1 — Consumo del feed (agnóstico)
- R1.1 CUANDO el Observador se construye, DEBERÁ recibir un MarketFeed y usar
  exclusivamente feed.next_event() y feed.now(); JAMÁS time.time() ni datetime.now().
- R1.2 El Observador DEBERÁ correr idéntico contra ReplayFeed y LiveFeed
  (test A1 propio: mismos episodios con mismos datos).
- R1.3 CUANDO llegue un Event FEED_GAP, el Observador DEBERÁ degradar el
  confidence del episodio activo de ese asset (no inventar continuidad).

## R2 — Ciclo de vida del episodio (PTM v3 §ciclo)
- R2.1 Por cada asset, el Observador DEBERÁ mantener a lo sumo UN episodio
  activo con estados QUIET→EXPANSION→PRESSURE→BRAKE→TRANSITION→RESOLUTION.
- R2.2 CUANDO el asset esté en QUIET y el rango/velocidad salga de su banda
  típica (definición versionada, formula_version), DEBERÁ abrir episodio en EXPANSION.
- R2.3 Las transiciones de estado DEBERÁN registrarse con ts del feed y
  Metric{raw,normalized,confidence,formula_version} del disparador.
- R2.4 CUANDO un episodio no progrese (timeout versionado por estado),
  DEBERÁ cerrarse con resolution_type=NEUTRALIZATION (nunca borrar).
- R2.5 El cierre de episodio DEBERÁ registrar resolution_type ∈
  {REBOUND, CONTINUATION, CHAOS, NEUTRALIZATION, FAILURE} básico (heurística
  v1 versionada; refinamiento MFE/MAE es Fase B).

## R3 — PressureCurve
- R3.1 Durante el episodio, cada vela cerrada M1 DEBERÁ producir un punto de
  la curva de presión (dirección dominante, avance neto, continuidad) como
  Metric completa.
- R3.2 La curva DEBERÁ persistirse íntegra (serie, no solo resumen).

## R4 — Persistencia
- R4.1 SQLite propio data/observador/episodes.db (WAL), tablas episodes,
  episode_states, pressure_points. Esquema = PTM v3 Fase A, con
  schema_version en tabla meta.
- R4.2 Todo episodio DEBERÁ guardar source del feed (REPLAY:*/LIVE:*) y
  JAMÁS mezclarse en consultas sin distinguirlo (R de FILOSOFIA).
- R4.3 Escrituras idempotentes: re-replay del mismo tramo con misma
  formula_version NO duplica episodios (clave natural asset+ts_inicio+source).

## R5 — Candados
- R5.1 El Observador NO DEBERÁ importar scanner, strat_fractal, ni nada del
  bot vivo; tampoco emitir órdenes ni señales. Solo escribe su DB.
- R5.2 El bot vivo NO se modifica en esta fase.

## Aceptación
- A1 Mismo consumidor contra ReplayFeed y stub → episodios idénticos.
- A2 E2E: 1 semana EURUSD M1 (ParquetSource) → termina, episodios >0,
  0 excepciones, reporte n_episodios/estados/duraciones.
- A3 Test adversarial: grep sin time.time()/datetime.now() en src/observador/.
- A4 Idempotencia: replay repetido → mismos episodios, sin duplicados.
- A5 Suite completa marketfeed+observador verde; regresión sin roturas nuevas.
