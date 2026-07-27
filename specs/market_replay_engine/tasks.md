# Tasks — Market Replay Engine (MRE)

Regla del repo: una task a la vez, test verde antes de marcar [x].
Trazabilidad R<n> ↔ test obligatoria (docs/verification.md).

- [x] T1. `src/marketfeed/base.py`: Event (dataclass frozen) + protocolo
      MarketFeed (next_event, now).
      Tests: test_marketfeed_base.py — construcción de eventos, inmutabilidad,
      kinds válidos. (R1.1, R2.1)

- [x] T2. `src/marketfeed/sources.py`: CsvSource (validación de esquema,
      dedup, orden, FEED_GAP en huecos).
      Tests: CSV sintético con duplicados y hueco de 3 velas M1 →
      n_servidas correcto, 1 FEED_GAP con (desde,hasta) exactos, error
      explícito con CSV de esquema inválido. (R2.3, R2.4, R6.3, R7.2)

- [x] T3. `sources.py`: BlackBoxSource (lectura solo-lectura de
      black_box_strat_*.db, extracción candles_1m/5m/15m, dedup por
      asset+tf+ts, anticontaminación 30% mediana, gaps, quality_report()).
      Tests: DB fixture pequeña construida en el test (no depender de las
      DBs reales) con velas repetidas entre snapshots y una vela contaminada
      → dedup y descarte verificados con números exactos. (R6.1, R6.2, R7.1)

- [x] T4. `src/marketfeed/replay.py`: ReplayFeed núcleo — merge heapq
      multi-fuente, now() avanza solo al consumir, factor de velocidad
      (sleep = delta/factor; MAX sin sleep), set_speed en caliente.
      Tests: con reloj mockeado, 2 velas delta=60s a 100x → sleep llamado
      con 0.6 (aritmética verificada: 60/100=0.6); a MAX → 0 llamadas a
      sleep; orden ts no-decreciente con 2 fuentes mezcladas; now() ==
      max(ts consumidos). (R2.3, R3.2, R4.1-R4.4)

- [x] T5. replay.py: Regla Sagrada — test adversarial: la API pública no
      expone lectura por delante del cursor; tras k eventos,
      now() == ts del último y ningún evento entregado tiene ts > now().
      (R3.1, R3.3, A3)

- [x] T6. replay.py: controles — pause/resume, step (exactamente 1 evento
      en pausa), seek(ts) con fast-forward sin sleeps y sin fuga de futuro,
      bookmark + export_bookmarks JSON.
      Tests: secuencia pause→step→step→resume; seek al medio de la sesión →
      primer evento posterior correcto y now() == ts buscado; bookmarks
      exportados con ts y nota. (R5.1-R5.4)

- [x] T7. `src/marketfeed/live_stub.py`: LiveFeed placeholder con
      get_candles inyectable, source='LIVE:quotex', now()=time.time().
      Tests: convierte velas inyectadas en Events bien formados. (R1.2)

- [x] T8. Integración A1: consumidor de prueba (cuenta velas y calcula
      última vela por asset usando SOLO feed.now(), jamás time.time())
      corre sin modificación contra ReplayFeed(fixture) y LiveFeed(stub) →
      mismos conteos. (R1.3, R1.4, A1)

- [x] T9. E2E A2: replay del día 2026-07-26 real completo a MAX →
      termina, quality_report con n servidas/descartadas/gaps, presupuesto
      < 5 min. Marcar en el reporte los totales para la bitácora. (A2, R7.1)
      RESULTADO 2026-07-27: 28,073 eventos (25,849 velas servidas + 2,224
      gaps) de 61 activos en 1.6 s a MAX. Descartes: 215,441 duplicados de
      snapshot, 3,570 contaminadas. Rango simulado 10:00→00:30. Regla
      Sagrada verificada en los 28,073 (ningún ts > now()).

- [x] T10. Candados R8: grep-test de que marketfeed no importa scanner/
      strat_fractal ni viceversa; suite completa de la feature verde;
      pytest de la familia existente sin nuevas roturas. (R8.2, A5)
      RESULTADO: suite marketfeed 23/23 verde en 0.23 s; grep de imports
      limpio; regresión completa = mismos 35 fallos PRE-EXISTENTES del bot
      con o sin marketfeed (859 passed) → cero roturas nuevas.

## Fuera de alcance (POSTPUESTO, ver requirements)
P1 seek_episode_start (necesita Observador/PTM).
P2 Descargadores Dukascopy/Binance.
P3 Migración del bot vivo a MarketFeed.
