# Design — Market Replay Engine (MRE)

Trazabilidad: cada sección referencia los R<n> de requirements.md.

## Ubicación y forma

Paquete NUEVO e independiente: `src/marketfeed/`
- `src/marketfeed/base.py`      — interfaz MarketFeed + tipos de evento (R1, R2)
- `src/marketfeed/replay.py`    — ReplayFeed + reloj simulado + controles (R3-R5)
- `src/marketfeed/sources.py`   — BlackBoxSource, CsvSource (R6, R7)
- `src/marketfeed/live_stub.py` — LiveFeed placeholder (R1.2, P3)
- `tests/test_marketfeed_*.py`  — suite propia, no toca tests existentes (R8.2, A5)

Cero imports desde scanner.py / strat_fractal.py hacia marketfeed y viceversa
(R8.2). El bot vivo no sabe que esto existe.

## Tipos (base.py)

```
Event = dataclass congelada:
    kind: 'CANDLE_CLOSED' | 'TICK' | 'FEED_GAP'
    asset: str
    ts: float            # timestamp SIMULADO (epoch)
    payload: dict        # ohlc+timeframe / price / (desde,hasta)
    source: str          # 'REPLAY:blackbox:2026-07-26' | 'LIVE:quotex' (R6.4)

class MarketFeed(Protocol):
    def next_event(self) -> Event | None   # None = fin de la historia
    def now(self) -> float                 # reloj del feed (R1.4, R3.2)
```

Decisión: `next_event()` bloqueante-simple (síncrono). Alternativas evaluadas:
- ALT A generador síncrono simple (ELEGIDA): trivial de testear, determinista,
  suficiente para un consumidor single-thread como el futuro Observador.
- ALT B asyncio: más fiel al websocket vivo, pero mete complejidad de event
  loop en la capa más fundacional; se puede envolver después sin romper la API.
- ALT C cola + thread productor: útil a 1x con muchos assets, innecesario
  para el caso de uso principal (MAX speed, un consumidor).

## Reloj simulado (replay.py) — R3, R4

- `self._now` arranca en el ts del primer evento y SOLO avanza al entregar
  un evento (R3.2). `now()` devuelve `self._now`.
- Velocidad: al entregar el evento k+1, `sleep(max(0, (ts_{k+1}-ts_k)/factor))`
  salvo factor MAX → sin sleep (R4.2, R4.3). `set_speed(x)` en caliente (R4.4).
- La Regla Sagrada se cumple por CONSTRUCCIÓN: el cursor de lectura es un
  iterador ordenado y no existe ningún método público que lea por delante
  del cursor (R3.1, R3.3). El merge multi-fuente usa heapq por (ts, asset,
  timeframe) → orden total determinista (R2.3).

## Controles (replay.py) — R5

- `pause()/resume()`: flag; `next_event()` en pausa bloquea salvo `step()`.
- `step()`: entrega exactamente 1 evento estando en pausa (R5.2).
- `seek(ts)`: reconstruye el heap desde las fuentes filtrando eventos ≤ ts
  ya consumidos — implementación simple: reset del iterador + fast-forward
  SIN sleeps hasta ts (garantiza cero fuga de futuro, R5.3). O(n) aceptable
  para sesiones de días; optimizar solo si el Atlas lo pide.
- `bookmark(nota)`: append a lista en memoria + `export_bookmarks(path)` JSON
  (R5.4). Persistencia simple archivo-por-sesión, sin DB.

## Fuentes (sources.py) — R6, R7

Interfaz interna `Source.iter_events() -> Iterator[Event]` (ordenados).

BlackBoxSource:
1. Lee scan_candidates de black_box_strat_YYYY-MM-DD.db (solo lectura).
2. Extrae velas de candles_1m/5m/15m JSON de cada snapshot.
3. Dedup por (asset, timeframe, ts) — los snapshots repiten velas (R6.2).
4. Anticontaminación: descarta vela con |precio - mediana_asset| > 30%
   mediana (criterio ya validado en el análisis forense) (R6.2).
5. Ordena, detecta huecos (> 1 período del timeframe) → FEED_GAP (R2.4).
6. Contadores por tramo: servidas/descartadas/huecos → `quality_report()`
   (R7.1).

CsvSource: columnas asset,timeframe,ts,o,h,l,c[,volume]; validación de
esquema con error explícito (R7.2). Mismo dedup/orden/gaps.

## LiveFeed placeholder (live_stub.py) — R1.2, R1.3, P3

Adaptador mínimo que envuelve una función inyectada `get_candles()` (la misma
firma que ya usa el bot para pedir velas) y las convierte en Events con
`now()=time.time()`. NO se conecta al scanner: se instancia solo en tests/
demos para probar A1. La migración real del bot es P3 (era Observador).

## Aritmética de referencia (verificada a mano, R4.3)

- 2 velas M1 consecutivas: delta=60s → 100x: 0.6s | 1000x: 0.06s | MAX: 0s.
- Día 26 caja negra ≈ velas únicas del orden de 10^4-10^5 tras dedup:
  a MAX es I/O-bound de SQLite+JSON, presupuesto A2: < 5 min.

## Estrategia de test (verification.md del repo)

- Unit: reloj (avance solo al consumir; sleep calculado 60/100=0.6 exacto en
  mock), dedup, anticontaminación, gaps, orden del heap, seek sin futuro.
- Adversarial (R3.3/A3): consumidor que busca en dir() del feed cualquier
  método que devuelva eventos > now() → no existe; y test de que tras
  consumir k eventos, max(ts servidos) == now().
- Integración (A1): consumidor de prueba (cuenta velas por asset) corre
  idéntico contra ReplayFeed(día 26) y LiveFeed stub con velas inyectadas.
- E2E (A2): replay completo día 26 a MAX + quality_report.
- Trazabilidad R<n> ↔ test en tasks.md (regla del repo).
