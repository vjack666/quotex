# Observador (Capa 2) — Tasks

- [x] T1. Leer contrato MarketFeed (base.py) y ReplayFeed (replay.py).
- [x] T2. requirements.md en notación EARS (este SDD).
- [x] T3. design.md: recorder como decorator de MarketFeed, parquet incremental.
- [x] T4. `src/marketfeed/recorder.py`: MarketRecorder (next_event/now/close,
      append incremental con ParquetWriter, schema R2.2).
- [x] T5. `tests/test_marketfeed_recorder.py`:
  - [x] implementa MarketFeed (isinstance con Protocol runtime_checkable)
  - [x] graba N CANDLE_CLOSED con columnas correctas
  - [x] parquet con exactamente N filas
  - [x] **test adversarial: la grabación nunca lee el futuro** — feed mock
        que lanza si next_event() se llama más veces que velas consumidas;
        el recorder solo graba lo ya ocurrido (Regla Sagrada R3).
  - [x] feed mock sintético local (sin importar el bot)
- [x] T6. Verificación: `PYTHONPATH=src pytest tests/test_marketfeed_recorder.py -q` verde.
- [ ] T7. **PUERTA HUMANA**: aprobación explícita antes de conectar el
      recorder a un LiveFeed real de Quotex (grabación OTC en vivo).
- [ ] T8. (Post-puerta) LiveFeed Quotex + rotación diaria de archivos parquet.
