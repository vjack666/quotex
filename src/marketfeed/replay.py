"""ReplayFeed — Market Replay Engine (T4, T5, T6).

Implementa el protocolo MarketFeed sobre múltiples Source, con merge
determinista por heapq y reloj lógico que avanza SOLO al consumir.

Regla Sagrada (R3): ninguna API pública devuelve o expone eventos con
ts > now(). El cursor solo avanza al entregar un evento.
"""
from __future__ import annotations

import heapq
import json
import time
from typing import Callable, List, Optional, Union

from marketfeed.base import Event, Source

MAX = "MAX"


class ReplayFeed:
    """Feed de replay síncrono multi-fuente.

    - speed: factor de velocidad (float) o 'MAX' (sin sleeps).
    - sleep_fn: inyectable para tests; default time.sleep.
    - now() arranca en el ts del primer evento entregado y avanza SOLO
      al consumir eventos.

    Semántica de pausa: next_event() en pausa devuelve None SIN avanzar
    el cursor (diseño síncrono, no bloqueante). Usar step() para
    entregar exactamente un evento estando en pausa.
    """

    def __init__(
        self,
        sources: List[Source],
        speed: Union[float, str] = MAX,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sources = list(sources)
        self._speed = speed
        self._sleep_fn = sleep_fn
        self._paused = False
        self._now: Optional[float] = None
        self._bookmarks: list = []
        self._build_heap()

    # ------------------------------------------------------------------ #
    # interno
    def _build_heap(self) -> None:
        """(Re)construye el heap de merge desde las fuentes."""
        self._heap = []
        self._iters = []
        for idx, src in enumerate(self._sources):
            it = iter(src.iter_events())
            self._iters.append(it)
            self._push_from(idx)

    def _push_from(self, idx: int) -> None:
        it = self._iters[idx]
        try:
            ev = next(it)
        except StopIteration:
            return
        # Orden total determinista: ts, asset, timeframe/kind, índice de fuente.
        tf = ev.payload.get("timeframe", 0) if isinstance(ev.payload, dict) else 0
        heapq.heappush(self._heap, (ev.ts, ev.asset, ev.kind, tf, idx, ev))

    def _pop(self) -> Optional[Event]:
        if not self._heap:
            return None
        ts, _asset, _kind, _tf, idx, ev = heapq.heappop(self._heap)
        self._push_from(idx)
        return ev

    def _deliver(self, do_sleep: bool) -> Optional[Event]:
        ev = self._pop()
        if ev is None:
            return None
        if do_sleep and self._speed != MAX and self._now is not None:
            delta = ev.ts - self._now
            if delta > 0:
                self._sleep_fn(delta / float(self._speed))
        self._now = ev.ts
        return ev

    # ------------------------------------------------------------------ #
    # API pública (lista blanca: next_event, now, pause, resume, step,
    # seek, bookmark, export_bookmarks, set_speed)
    def next_event(self) -> Optional[Event]:
        """Siguiente evento en orden de ts, o None al agotar la historia.

        En pausa devuelve None SIN avanzar el cursor (síncrono, no
        bloqueante); usar step() para avanzar exactamente un evento.
        """
        if self._paused:
            return None
        return self._deliver(do_sleep=True)

    def now(self) -> float:
        """Reloj del feed: ts del último evento entregado (R3.2)."""
        return self._now if self._now is not None else 0.0

    def set_speed(self, speed: Union[float, str]) -> None:
        """Cambia el factor de velocidad en caliente ('MAX' o float > 0)."""
        if speed != MAX and float(speed) <= 0:
            raise ValueError("speed debe ser > 0 o 'MAX'")
        self._speed = speed

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def step(self) -> Optional[Event]:
        """Entrega exactamente 1 evento (sin sleep), incluso en pausa."""
        return self._deliver(do_sleep=False)

    def seek(self, ts: float) -> None:
        """Reconstruye desde las fuentes y consume sin sleep hasta ts.

        Al terminar, now() == ts del último evento con ts <= ts objetivo
        (sin fuga de futuro: nada con ts > objetivo se entrega ni expone).
        """
        self._now = None
        self._build_heap()
        while self._heap and self._heap[0][0] <= ts:
            self._deliver(do_sleep=False)

    def bookmark(self, nota: str) -> None:
        """Registra (now(), nota) en la lista de bookmarks."""
        self._bookmarks.append({"ts": self.now(), "nota": nota})

    def export_bookmarks(self, path: str) -> None:
        """Escribe los bookmarks como JSON [{ts, nota}] en path."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._bookmarks, f, ensure_ascii=False, indent=2)
