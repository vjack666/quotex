# Market Replay Engine — Diseño conceptual (Capa 0.5: el Túnel del Tiempo)

Estado: DISEÑO APROBADO EN CONCEPTO, pendiente de spec SDD antes de código.
Relación: sirve a la Capa 2 (Observador) y a la Capa 3 (Atlas). Ver FILOSOFIA.md.

> "Un simulador de vuelo para traders, no un backtester."

## Misión

Reproducir el mercado exactamente como un feed en vivo, para que el
Observador viva meses de mercado en horas y el Atlas se llene de miles
de episodios sin esperar el tiempo real.

NO es backtesting de estrategias. Es aceleración de la OBSERVACIÓN.

## La Regla Sagrada (única no negociable)

EL OBSERVADOR NUNCA VE EL FUTURO.
El Replay entrega el pasado gota a gota, en orden, sin excepciones.
Ninguna API del feed permite pedir "la vela siguiente" antes de tiempo,
ni estadísticas que incluyan datos posteriores al reloj simulado.
Violación de esta regla = todo el Atlas generado queda contaminado.

## Arquitectura: una sola interfaz

```
MarketFeed (interfaz única)
  next_event() -> Event
  now() -> reloj del feed (real o simulado)

Implementaciones:
  LiveFeed    — Quotex hoy (websocket/pyquotex)
  ReplayFeed  — historia grabada, velocidad configurable
  (mañana: MT5Feed, BinanceFeed, DukascopyFeed, CsvFeed)
```

El Observador consume MarketFeed y NO PUEDE SABER cuál hay detrás.
Cambiar de vivo a replay = cambiar configuración, cero código del
Observador. (Mismo patrón que instrument_readings en PTM v3: el
concepto no conoce al instrumento.)

## Eventos, no velas

El feed emite EVENTOS tipados con timestamp del reloj simulado:

  CANDLE_CLOSED   (asset, timeframe, ohlc)      — del feed
  TICK            (asset, price, ts)             — del feed, si hay
  FEED_GAP        (asset, desde, hasta)          — hueco declarado

Los eventos de nivel superior (PRESSURE_CHANGED, ENTERED_ATTENTION_ZONE,
BRAKE_STARTED, TRANSITION_DETECTED...) NO los emite el feed: los emite
el OBSERVADOR al procesar los eventos del feed. El feed es tonto a
propósito — solo mercado crudo. Así el vivo y el replay son
indistinguibles por construcción.

## Reloj simulado

- Velocidades: 1x, 10x, 100x, 1000x, MAX (sin espera entre eventos).
- El Observador jamás llama a time.time(): usa feed.now().
  (Esta es la única regla de implementación que el Observador debe
  respetar para ser replay-compatible. Todo timestamp del PTM sale
  del reloj del feed.)
- Aritmética de referencia: 1 vela M1 cada 10 ms => 1 día ≈ 15 s,
  1 mes ≈ 7 min, 1 año ≈ 1.5 h (orden de magnitud, depende del motor).

## Controles de simulador de vuelo

  pause() / resume()
  step()                    — avanzar UN evento (vela a vela)
  seek_episode_start(id)    — retroceder al inicio de un episodio
  bookmark(nota)            — marcar momento interesante
  speed(x)                  — cambiar velocidad en caliente

Uso previsto: revisar con ojo humano los episodios que el Atlas señale,
reproducirlos vela a vela, y etiquetarlos (el campo "etiqueta humana"
del PTM v3). El Replay convierte el etiquetado del Atlas en ver
televisión con pausa, no en leer tablas.

## Fuentes de historia (realidad de datos a 2026-07-27)

1. Caja negra propia: 11 días (17→27 jul, 132 MB). Velas por snapshot
   de scan, no continuas => reconstruible por TRAMOS alrededor de
   actividad, con huecos declarados via FEED_GAP. Gratis y ya nuestra.
   Cobertura: los activos que el bot escaneó, incluidos OTC.
2. Histórico externo (Dukascopy forex / Binance cripto): años de velas
   continuas para pares estándar. Limitación honesta: los OTC exóticos
   de Quotex NO existen fuera de Quotex; el replay masivo entrena al
   Observador en pares reales, y los OTC se calibran con lo capturado
   en vivo.
3. A futuro: el propio Observador en vivo graba feed crudo continuo
   (no solo snapshots), engordando la historia replayable cada día.

Todo tramo replayado lleva su calidad estampada (contrato de calidad
del PTM v3): huecos y resampleos bajan el confidence de las Metrics
de ese tramo. El Atlas puede filtrar "solo episodios de tramo limpio".

## Qué NO es

- NO ejecuta órdenes, no simula broker, no calcula P&L (eso sería
  backtest = capa de negocio; Principio 7).
- NO optimiza parámetros de estrategias barriendo la historia
  (eso es el Laboratorio, y pasa por el tribunal de falsación).
- NO inventa datos: si no hay velas de un tramo, emite FEED_GAP,
  jamás interpola en silencio (lección del bug de velas cruzadas).

## Advertencia científica (para el Atlas)

Los episodios generados por replay se etiquetan source=REPLAY con su
fuente de datos. Episodios de replay y de vivo NUNCA se mezclan sin
distinción en un análisis: el feed vivo de Quotex (OTC, spreads, su
"sabor" de precios) no es idéntico a Dukascopy. El replay acelera el
APRENDIZAJE del fenómeno; la validación final de cualquier regla se
hace sobre episodios vivos. Mismo tribunal, mismo estándar.

## Orden de construcción sugerido (cuando se apruebe)

1. Interfaz MarketFeed + ReplayFeed desde caja negra propia (tramos).
2. Adaptar el futuro Observador a feed.now() desde el día uno
   (nace replay-compatible, no se adapta después).
3. Descargador Dukascopy/Binance (ya existe precedente en el proyecto
   SMC-SYSTEMS de descarga histórica verificada).
4. Controles de vuelo (pause/step/seek/bookmark) — para el etiquetado.
