# Observador (Capa 2) — Requirements (EARS)

Documentos rectores: docs/FILOSOFIA.md, specs/market_replay_engine/,
specs/freno_observador_rentabilidad/CONTRATO.md.

Propósito: GRABAR el mercado en vivo (caja negra local en parquet) para que
señales como el freno (muerte del impulso, 91% WR en M15) nazcan de datos
frescos/OTC y se validen en entorno real. La Constitución dicta:
"EURUSD real ≠ OTC Quotex" — no se extrapola sin grabar el propio mercado.

## R1 — Interfaz única
- R1.1 The recorder SHALL implement the `MarketFeed` protocol
  (`next_event()`, `now()`) de `src/marketfeed/base.py`.
- R1.2 WHEN a consumer swaps `ReplayFeed` for `MarketRecorder(live_feed)`,
  the consumer code SHALL NOT change (vivo y replay son indistinguibles).

## R2 — Grabación
- R2.1 WHEN `next_event()` returns an event with kind `CANDLE_CLOSED`,
  the recorder SHALL append one row to the parquet output.
- R2.2 The parquet schema SHALL be
  `{time, open, high, low, close, volume, tick_volume, asset, tf, kind}`.
- R2.3 The recorder SHALL append incrementally (row-group append via
  ParquetWriter), never reloading nor rewriting the file.
- R2.4 Events with kind other than `CANDLE_CLOSED` (TICK, FEED_GAP)
  SHALL be passed through without recording.
- R2.5 `close()` SHALL flush and close the parquet writer; after close the
  file SHALL be readable by `pandas.read_parquet`.

## R3 — Regla Sagrada (no ver el futuro)
- R3.1 The recorder SHALL NOT call the underlying feed except inside its
  own `next_event()`; it records ONLY events already delivered.
- R3.2 `now()` SHALL return the ts of the last delivered event (delegated
  to the underlying feed cursor); nothing with ts > now() is ever exposed
  or written.
- R3.3 The recorder SHALL NOT use wall clock (`time.time()`,
  `datetime.now()`); all timestamps come from the events themselves.

## R4 — Aislamiento
- R4.1 The recorder SHALL NOT import bot modules (scanner, strat_fractal,
  pyquotex, consolidation_bot, connection, caffeine, loop_utils).
- R4.2 IF the underlying feed is exhausted (returns None), THEN
  `next_event()` SHALL return None without touching the writer.

## Puerta humana
- La activación del Observador contra el feed LIVE de Quotex requiere
  aprobación humana explícita (no se conecta al bróker en esta fase).
