from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class CrossRecord:
    asset: str
    direction: str
    idx: int
    k_last: float
    d_last: float
    ts: str
    consumed: bool = False
    meta: Dict[str, Optional[float]] = field(default_factory=dict)


class StochCrossState:
    """Semáforo singleton por asset+dir. Guarda el instante del cruce M15
    para que el pipeline pregunte "ya cruzó?" sin recalcular la serie.
    """

    _instance: Optional["StochCrossState"] = None
    _lock_cls = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[tuple[str, str], CrossRecord] = {}

    @classmethod
    def get(cls) -> "StochCrossState":
        with cls._lock_cls:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def register_cross(
        self,
        asset: str,
        direction: str,
        idx: int,
        k_last: float,
        d_last: float,
        ts: Optional[str] = None,
        separation: Optional[float] = None,
        intent_band_hit: Optional[float] = None,
    ) -> None:
        key = (asset, direction.upper())
        rec = CrossRecord(
            asset=asset,
            direction=direction.upper(),
            idx=int(idx),
            k_last=float(k_last),
            d_last=float(d_last),
            ts=str(ts or datetime.now(timezone.utc).isoformat()),
            consumed=False,
            meta={
                "separation": float(separation) if separation is not None else None,
                "intent_band_hit": float(intent_band_hit) if intent_band_hit is not None else None,
            },
        )
        with self._lock:
            self._data[key] = rec
        log.debug("[CROSS_STATE] registered %s", self._redact(rec))

    def get_cross(self, asset: str, direction: str) -> Optional[CrossRecord]:
        key = (asset, direction.upper())
        with self._lock:
            record = self._data.get(key)
            if record and not record.consumed:
                return record
            return None

    def consume(self, asset: str, direction: str) -> None:
        key = (asset, direction.upper())
        with self._lock:
            record = self._data.get(key)
            if record:
                record.consumed = True
                log.debug("[CROSS_STATE] consumed %s", self._redact(record))

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._data.values() if not r.consumed)

    def reset(self) -> None:
        with self._lock:
            self._data.clear()

    @staticmethod
    def _redact(rec: CrossRecord) -> str:
        return (
            f"{rec.asset} {rec.direction} idx={rec.idx} k={rec.k_last:.2f} d={rec.d_last:.2f}"
            f" sep={(rec.meta.get('separation'))} band={rec.meta.get('intent_band_hit')}"
        )
