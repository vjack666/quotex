# Tasks — Observador Fase A: Núcleo de Episodios

Regla del repo: una task a la vez, test verde antes de [x]. Trazabilidad R↔test.

- [ ] T1. src/observador/metric.py — Metric{raw,normalized,confidence,
      formula_version} frozen + validación. Tests: construcción, inmutable,
      confidence ∈ [0,1]. (PTM v3)

- [x] T2. src/observador/pressure.py — punto de PressureCurve por vela M1
      (dirección, avance neto, continuidad) con aritmética verificada a mano
      en tests. (R3.1)

- [x] T3. src/observador/state_machine.py — EpisodeStateMachine con
      quiet_exit_v1 + transitions_v1 + timeouts→NEUTRALIZATION. Tests: una
      secuencia sintética por cada transición (QUIET→EXPANSION, →PRESSURE,
      →BRAKE, →TRANSITION, →RESOLUTION con REBOUND/CONTINUATION/CHAOS) y
      timeout. (R2.1-R2.5)

- [x] T4. src/observador/store.py — SQLite WAL, esquema D4, UPSERT
      idempotente, schema_version. Tests: persistir episodio completo,
      releer, doble escritura sin duplicados. (R4.1-R4.3)

- [x] T5. src/observador/observer.py — loop multi-asset sobre MarketFeed,
      manejo FEED_GAP (confidence ×0.5), cero time.time(). Tests: feed fake
      con 2 assets mezclados → 2 episodios independientes; gap degrada
      confidence. (R1.1, R1.3, D6)

- [x] T6. Integración A1: mismo Observador contra ReplayFeed(fixture) y
      LiveFeed(stub) con mismas velas → episodios idénticos. (R1.2, A1)

- [x] T7. Idempotencia A4: replay del mismo tramo 2 veces → mismos episodios,
      count igual. (R4.3, A4)

- [x] T8. Adversarial A3: test que grep-ea src/observador/ y falla si
      aparece time.time()/datetime.now()/datetime.utcnow(). (A3)

- [x] T9. E2E A2: 1 semana EURUSD M1 real (ParquetSource, skipif sin
      archivo) → episodios >0, 0 excepciones, reporte a bitácora
      (n_episodios, distribución de resoluciones, duración media). (A2)

- [x] T10. Candados + regresión: grep imports bot vivo, suite completa
      marketfeed+observador verde, pytest global sin roturas nuevas. (R5, A5)


## Bitácora T9 (E2E real, 2026-07-27)
EURUSD M1 13→20 jul (ParquetSource SMC-SYSTEMS), ReplayFeed MAX:
7,191 eventos → 158 episodios, 2,694 pressure_points, 1.2s.
Resoluciones: CONTINUATION 66 (42%), REBOUND 51 (32%), CHAOS 37 (23%),
NEUTRALIZATION 4 (3%). Duración media 15-17 min. DB: data/observador/episodes_t9_smoke.db

## Bitácora T10
Candado imports bot vivo: limpio. Suite observador+marketfeed: 64 passed.
Regresión global: 900 passed, 35 failed PRE-EXISTENTES (idénticos a antes de la feature).
