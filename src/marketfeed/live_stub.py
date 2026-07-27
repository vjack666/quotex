"""LiveFeed stub — PLACEHOLDER (R1.2, P3 postpuesto).

ATENCIÓN: esto es un PLACEHOLDER solo para tests/demos. NO conecta con el
bot vivo ni con Quotex. La migración real del bot a MarketFeed es P3
(postpuesto, ver specs/market_replay_engine/requirements). El callable
`get_candles(asset, timeframe)` se INYECTA desde fuera; aquí solo se
convierte su salida en Events del contrato MarketFeed.
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional

from marketfeed.base import Event, KIND_CANDLE_CLOSED


class LiveFeed:
    """Implementación LIVE placeholder del protocolo MarketFeed.

    - next_event(): round-robin sobre `assets`; llama get_candles(asset,
      timeframe), convierte velas con ts no visto en Event
      kind=CANDLE_CLOSED source='LIVE:quotex'. Devuelve None si no hay
      nada nuevo en una vuelta completa.
    - now(): time.time() (reloj real, R1.2).
    """

    SOURCE = "LIVE:quotex"

    def __init__(self, get_candles: Callable, assets: List[str], timeframe: int = 60):
        if not assets:
            raise ValueError("assets vacío")
        self._get_candles = get_candles
        self._assets = list(assets)
        self._timeframe = int(timeframe)
        self._idx = 0
        self._seen = set()  # (asset, ts) ya emitidos
        self._pending: List[Event] = []

    def _candle_to_event(self, asset: str, candle: dict) -> Event:
        payload = {
            "timeframe": self._timeframe,
            "open": candle.get("open"),
            "high": candle.get("high"),
            "low": candle.get("low"),
            "close": candle.get("close"),
        }
        if "volume" in candle:
            payload["volume"] = candle["volume"]
        return Event(
            kind=KIND_CANDLE_CLOSED,
            asset=asset,
            ts=float(candle["ts"]),
            payload=payload,
            source=self.SOURCE,
        )

    def next_event(self) -> Optional[Event]:
        if self._pending:
            return self._pending.pop(0)
        for _ in range(len(self._assets)):
            asset = self._assets[self._idx]
            self._idx = (self._idx + 1) % len(self._assets)
            candles = self._get_candles(asset, self._timeframe) or []
            nuevos = []
            for c in candles:
                key = (asset, float(c["ts"]))
                if key in self._seen:
                    continue
                self._seen.add(key)
                nuevos.append(self._candle_to_event(asset, c))
            if nuevos:
                nuevos.sort(key=lambda e: e.ts)
                self._pending = nuevos[1:]
                return nuevos[0]
        return None

    def now(self) -> float:
        return time.time()
