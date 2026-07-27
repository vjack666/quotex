# Requirements — Market Replay Engine (MRE)

Feature: market_replay_engine
Capa: 0.5 (fuente de datos / túnel del tiempo). Sirve al futuro Observador (Capa 2).
Documentos rectores: docs/FILOSOFIA.md, docs/PTM_V3.md, docs/REPLAY_ENGINE.md.
Notación: EARS (WHEN/WHILE/IF ... THE SYSTEM SHALL ...).

## Contexto y objetivo

Reproducir mercado histórico como si fuera un feed en vivo, evento a evento,
para que el Observador (cuando exista) y cualquier consumidor futuro no puedan
distinguir vivo de replay. NO es backtesting: no ejecuta órdenes, no simula
broker, no calcula P&L. Acelera la observación y la generación del Atlas.

## R1 — Interfaz única MarketFeed

R1.1 WHEN un consumidor solicita el siguiente evento, THE SYSTEM SHALL
     entregarlo mediante una interfaz única `MarketFeed` con exactamente dos
     operaciones de consumo: `next_event()` y `now()`.
R1.2 THE SYSTEM SHALL proveer al menos dos implementaciones: `ReplayFeed`
     (esta feature) y un adaptador `LiveFeed` PLACEHOLDER que envuelve el feed
     Quotex actual SIN modificar el scanner ni el bot vivo (solo lectura del
     mismo stream de velas que ya llega).
R1.3 IF el consumidor cambia de LiveFeed a ReplayFeed, THEN el cambio SHALL
     requerir únicamente configuración (parámetro/config), cero cambios de
     código en el consumidor. Test: el mismo consumidor de prueba corre contra
     ambos feeds sin editar su código.
R1.4 El consumidor NUNCA SHALL necesitar `time.time()`: todo timestamp
     observable proviene de `feed.now()`.

## R2 — Eventos crudos, tipados, en orden

R2.1 THE SYSTEM SHALL emitir únicamente eventos CRUDOS de mercado:
     `CANDLE_CLOSED(asset, timeframe, ohlc, ts)`, `TICK(asset, price, ts)`
     (si la fuente los tiene) y `FEED_GAP(asset, ts_desde, ts_hasta)`.
R2.2 Los eventos de nivel superior (cambio de presión, entrada en zona,
     transición) NO SHALL ser emitidos por el feed: pertenecen al Observador.
R2.3 WHEN se emiten eventos, THE SYSTEM SHALL entregarlos en orden
     estrictamente no-decreciente de timestamp simulado; empates se resuelven
     por orden determinista (asset, timeframe).
R2.4 IF la fuente histórica tiene un hueco (velas faltantes) THE SYSTEM SHALL
     emitir `FEED_GAP` explícito y NUNCA interpolar ni inventar velas.

## R3 — Regla Sagrada: el futuro no existe

R3.1 THE SYSTEM SHALL NOT exponer ninguna operación que devuelva datos con
     timestamp posterior a `now()` (ni lookahead, ni agregados, ni conteos).
R3.2 `now()` SHALL avanzar únicamente cuando se consume un evento.
R3.3 Test de caja negra obligatorio: un consumidor adversarial que intente
     obtener la vela siguiente sin consumirla SHALL fallar (no existe API).

## R4 — Velocidad configurable

R4.1 THE SYSTEM SHALL soportar factores de velocidad 1x, 10x, 100x, 1000x y
     MAX (sin espera alguna entre eventos).
R4.2 WHILE el factor es Nx, el tiempo de pared entre dos eventos SHALL ser
     (delta_simulado / N), con precisión mejor-esfuerzo (sleep del SO).
R4.3 WHEN el factor es MAX, THE SYSTEM SHALL emitir sin sleep (limitado solo
     por CPU/IO). Ejemplo verificado a mano: dos velas M1 consecutivas
     (delta simulado = 60 s) a 100x → espera de pared = 60/100 = 0.6 s;
     a 1000x → 0.06 s; a MAX → 0 s.
R4.4 THE SYSTEM SHALL permitir cambiar la velocidad en caliente sin reiniciar
     la sesión de replay.

## R5 — Controles de simulador de vuelo

R5.1 THE SYSTEM SHALL soportar `pause()` y `resume()`.
R5.2 THE SYSTEM SHALL soportar `step()`: WHILE está en pausa, entrega
     exactamente UN evento y vuelve a pausa.
R5.3 THE SYSTEM SHALL soportar `seek(ts)`: reposicionar el cursor a un
     timestamp simulado T. Tras un seek, el estado interno del feed se
     reconstruye SOLO con eventos ≤ T (sin fugas de futuro).
     Nota: `seek_episode_start(id)` se implementa como azúcar sobre `seek(ts)`
     cuando exista el Observador que defina episodios — ver POSTPUESTO P1.
R5.4 THE SYSTEM SHALL soportar `bookmark(nota)`: registrar (ts_simulado,
     nota, fuente) en una lista persistente de la sesión de replay,
     exportable a JSON.

## R6 — Fuentes de historia

R6.1 THE SYSTEM SHALL leer como primera fuente las cajas negras propias
     (data/db/black_box_strat_*.db, 11 días al 2026-07-27), reconstruyendo
     tramos de velas alrededor de la actividad grabada y declarando
     FEED_GAP entre tramos.
R6.2 THE SYSTEM SHALL deduplicar velas repetidas entre snapshots de scan
     (misma asset+timeframe+ts → una sola vela) y descartar velas
     contaminadas según el criterio anticontaminación ya validado
     (precio a >30% de la mediana del activo en la fuente).
R6.3 THE SYSTEM SHALL soportar una fuente CSV genérica
     (asset,timeframe,ts,o,h,l,c[,volume]) para históricos externos
     (Dukascopy/Binance) SIN implementar en esta feature los descargadores.
R6.4 Cada sesión de replay SHALL declarar sus fuentes y estampar
     `source=REPLAY` + identificador de fuente en todo evento, para que
     ningún consumidor pueda mezclar episodios replay/vivo sin distinción.

## R7 — Calidad de datos

R7.1 WHEN un tramo contiene huecos, deduplicaciones o descartes por
     contaminación, THE SYSTEM SHALL reportar por tramo: n velas servidas,
     n descartadas, n huecos — consultable al final de la sesión.
R7.2 THE SYSTEM SHALL rechazar (con error explícito, no silencioso) fuentes
     cuyo esquema no pueda validar.

## R8 — No-objetivos (candados)

R8.1 THE SYSTEM SHALL NOT ejecutar órdenes, simular broker, ni calcular P&L.
R8.2 THE SYSTEM SHALL NOT modificar scanner.py, strat_fractal.py ni ningún
     módulo del bot vivo. El bot actual ni se entera de que el MRE existe.
R8.3 THE SYSTEM SHALL NOT emitir señales ni opiniones: solo mercado crudo.

## POSTPUESTO (declarado, no medio-prometido)

P1 `seek_episode_start(episode_id)`: requiere que exista el Observador y su
   tabla de episodios (PTM v3). Hasta entonces, solo `seek(ts)` genérico.
   Razón: no hay episodios que buscar todavía.
P2 Descargadores Dukascopy/Binance: la feature entrega el lector CSV
   genérico; la descarga masiva externa es feature aparte.
P3 LiveFeed completo de producción: aquí solo el adaptador placeholder de
   lectura para probar R1.3; la migración del scanner al MarketFeed es
   decisión de la era Observador, no de esta feature.

## Criterios de aceptación globales

A1 Un consumidor de prueba corre idéntico contra ReplayFeed (caja negra
   día 26) y contra el LiveFeed placeholder, sin cambiar su código (R1.3).
A2 Replay del día 26 completo a MAX termina y reporta n eventos, n gaps,
   n descartes, en tiempo razonable (< minutos, no horas).
A3 Test adversarial de futuro (R3.3) en verde.
A4 pause/step/seek/bookmark demostrados en test de integración.
A5 pytest de la feature 100% verde sin tocar tests existentes del bot.
