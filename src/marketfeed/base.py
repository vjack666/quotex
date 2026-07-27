"""MarketFeed — contrato base del Market Replay Engine (Capa 0.5).

Documentos rectores: docs/FILOSOFIA.md, docs/REPLAY_ENGINE.md,
specs/market_replay_engine/ (R1, R2).

Regla Sagrada (R3): ningún consumidor puede ver eventos con ts > now().
Regla de consumo (R1.4): el consumidor JAMÁS usa time.time(); usa feed.now().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional, Protocol, runtime_checkable

# Tipos de evento CRUDO permitidos (R2.1). Los eventos ricos (presión,
# zona, transición) pertenecen al Observador, no al feed (R2.2).
KIND_CANDLE_CLOSED = "CANDLE_CLOSED"
KIND_TICK = "TICK"
KIND_FEED_GAP = "FEED_GAP"
VALID_KINDS = frozenset({KIND_CANDLE_CLOSED, KIND_TICK, KIND_FEED_GAP})


@dataclass(frozen=True)
class Event:
    """Evento crudo de mercado. Inmutable (frozen).

    payload por kind:
      CANDLE_CLOSED: {"timeframe": int_seg, "open","high","low","close", opc "volume"}
      TICK:          {"price": float}
      FEED_GAP:      {"ts_desde": float, "ts_hasta": float}
    source (R6.4): p.ej. "REPLAY:blackbox:2026-07-26" | "REPLAY:csv:<file>" | "LIVE:quotex"
    """

    kind: str
    asset: str
    ts: float
    payload: dict = field(default_factory=dict)
    source: str = ""

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"kind inválido: {self.kind!r}; permitidos: {sorted(VALID_KINDS)}")
        if not self.asset:
            raise ValueError("asset vacío")
        if not isinstance(self.ts, (int, float)):
            raise ValueError(f"ts debe ser numérico, no {type(self.ts).__name__}")


@runtime_checkable
class MarketFeed(Protocol):
    """Interfaz única (R1.1). LiveFeed y ReplayFeed la implementan.

    Cambiar de implementación = configuración, nunca código del consumidor (R1.3).
    """

    def next_event(self) -> Optional[Event]:
        """Entrega el siguiente evento en orden de ts, o None al agotar la historia."""
        ...

    def now(self) -> float:
        """Reloj del feed. En replay avanza SOLO al consumir eventos (R3.2)."""
        ...


class Source(Protocol):
    """Fuente interna de historia. Debe producir eventos ordenados por ts."""

    def iter_events(self) -> Iterator[Event]:
        ...

    def quality_report(self) -> dict:
        """{'served': int, 'discarded': int, 'gaps': int, ...} (R7.1)."""
        ...
