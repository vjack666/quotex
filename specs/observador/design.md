# Observador (Capa 2) — Design

## Arquitectura

```
LiveFeed / ReplayFeed  ──►  MarketRecorder (decorator, implementa MarketFeed)
        (inyectado)              │ next_event(): consume 1 evento del feed
                                 │ si kind == CANDLE_CLOSED → append parquet
                                 ▼
                     data/observador/<asset>_<tf>.parquet (caja negra)
```

`MarketRecorder` es un **decorator transparente** sobre cualquier
`MarketFeed`. El consumidor no distingue vivo de replay ni grabado de
no-grabado: recibe los mismos `Event` en el mismo orden (R1.2). Cambiar de
implementación es configuración, nunca código del consumidor.

## Componentes

- `MarketRecorder(feed: MarketFeed, out_path: str|Path, buffer_size: int = 1)`
  - `next_event()` → `feed.next_event()`; si el evento es CANDLE_CLOSED,
    serializa una fila y la escribe con `pyarrow.parquet.ParquetWriter`
    (append incremental por row-group, sin recargar el archivo — R2.3).
  - `now()` → delega en `feed.now()` (reloj lógico, R3.2).
  - `close()` → flush del buffer y cierre del writer (R2.5).
  - Context manager (`__enter__`/`__exit__`) por comodidad.

## Schema parquet (R2.2)

| col          | tipo    | fuente                                   |
|--------------|---------|------------------------------------------|
| time         | float64 | `Event.ts`                               |
| open..close  | float64 | `payload["open"|"high"|"low"|"close"]`   |
| volume       | float64 | `payload.get("volume", 0.0)`             |
| tick_volume  | int64   | `payload.get("tick_volume", 0)`          |
| asset        | str     | `Event.asset`                            |
| tf           | int64   | `payload.get("timeframe", 0)` (segundos) |
| kind         | str     | `Event.kind` (siempre CANDLE_CLOSED)     |

## Regla Sagrada

El recorder no tiene ningún método que itere el feed por su cuenta: la ÚNICA
lectura del feed subyacente ocurre dentro de `next_event()` cuando el
consumidor lo pide. Por construcción no puede leer (ni grabar) el futuro.
Test adversarial: un feed mock que explota si se le piden más eventos de los
existentes demuestra que grabar N eventos ⇒ exactamente N llamadas al feed.

## No-goals
- No toca el bot ni el bróker (sin imports de scanner/pyquotex/etc.).
- No emite eventos ricos (presión/zona): eso es fase posterior del Observador.
- No usa reloj de pared.
