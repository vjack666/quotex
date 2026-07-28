"""MarketRecorder — Observador (Capa 2), caja negra local en parquet.

SDD: specs/observador/{requirements,design,tasks}.md.

Decorator transparente sobre cualquier MarketFeed: entrega los mismos
eventos y graba cada CANDLE_CLOSED a parquet con append incremental.

Regla Sagrada (R3): la única lectura del feed subyacente ocurre dentro de
next_event(); solo se graba lo ya ocurrido. Cero reloj de pared.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pyarrow as pa
import pyarrow.parquet as pq

from marketfeed.base import KIND_CANDLE_CLOSED, Event, MarketFeed

SCHEMA = pa.schema(
    [
        ("time", pa.float64()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.float64()),
        ("tick_volume", pa.int64()),
        ("asset", pa.string()),
        ("tf", pa.int64()),
        ("kind", pa.string()),
    ]
)


def _row_from_event(ev: Event) -> dict:
    """Serialize a CANDLE_CLOSED event into one parquet row (R2.2)."""
    p = ev.payload or {}
    return {
        "time": float(ev.ts),
        "open": float(p["open"]),
        "high": float(p["high"]),
        "low": float(p["low"]),
        "close": float(p["close"]),
        "volume": float(p.get("volume", 0.0)),
        "tick_volume": int(p.get("tick_volume", 0)),
        "asset": ev.asset,
        "tf": int(p.get("timeframe", 0)),
        "kind": ev.kind,
    }


class MarketRecorder:
    """Implements MarketFeed; records CANDLE_CLOSED events to parquet.

    - feed: underlying MarketFeed (live or replay), injected.
    - out_path: destination parquet file.
    - buffer_size: rows per row-group flush (>=1). Incremental append,
      never reloads the file (R2.3).
    """

    def __init__(
        self,
        feed: MarketFeed,
        out_path: Union[str, Path],
        buffer_size: int = 1,
    ) -> None:
        if buffer_size < 1:
            raise ValueError("buffer_size debe ser >= 1")
        self._feed = feed
        self._out_path = Path(out_path)
        self._buffer_size = buffer_size
        self._buffer: list[dict] = []
        self._writer: Optional[pq.ParquetWriter] = None
        self._closed = False

    # ------------------------------------------------------------------ #
    # MarketFeed protocol
    def next_event(self) -> Optional[Event]:
        """Delegate to the underlying feed; record CANDLE_CLOSED (R2.1).

        Never pulls ahead: exactly one underlying call per call (R3.1).
        """
        ev = self._feed.next_event()
        if ev is not None and ev.kind == KIND_CANDLE_CLOSED:
            self._buffer.append(_row_from_event(ev))
            if len(self._buffer) >= self._buffer_size:
                self._flush()
        return ev

    def now(self) -> float:
        """Logical clock, delegated to the underlying feed (R3.2)."""
        return self._feed.now()

    # ------------------------------------------------------------------ #
    def _flush(self) -> None:
        if not self._buffer:
            return
        table = pa.Table.from_pylist(self._buffer, schema=SCHEMA)
        if self._writer is None:
            self._out_path.parent.mkdir(parents=True, exist_ok=True)
            self._writer = pq.ParquetWriter(self._out_path, SCHEMA)
        self._writer.write_table(table)
        self._buffer = []

    def close(self) -> None:
        """Flush pending rows and close the parquet writer (R2.5)."""
        if self._closed:
            return
        self._flush()
        if self._writer is not None:
            self._writer.close()
        self._closed = True

    # context manager sugar
    def __enter__(self) -> "MarketRecorder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
