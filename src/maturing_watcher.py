"""maturing_watcher — Observador liviano del MaturingWatchlist.

NO es el Observador PTM v3 (state machine, parquet, episodes).
Es una capa de métricas en memoria con logging barato por ciclo.

Uso:
    watcher = MaturingWatcher(maturing_watchlist)
    # El watchlist llama watcher.on_capture/promote/drop automáticamente
    # cuando se setea watcher.watchlist._watcher = watcher
    # Al final de cada ciclo de scan: watcher.on_cycle_end()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from maturing_watchlist import MaturingEntry, MaturingWatchlist

log = logging.getLogger(__name__)


@dataclass
class CycleSnapshot:
    """Métricas de un ciclo de scan individual."""

    ts: float
    captured: int
    promoted_live: int
    promoted_shadow: int
    dropped: dict[str, int]
    active_before: int
    active_after: int
    avg_bars_age: float
    total_bars_age: int


class _CycleAccumulator:
    """Acumulador reseteable por ciclo."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.captured = 0
        self.promoted_live = 0
        self.promoted_shadow = 0
        self.dropped: dict[str, int] = field(default_factory=dict)
        self.active_before = 0


class MaturingWatcher:
    """Observador liviano del MaturingWatchlist.

    Se conecta via `watchlist._watcher = watcher`. Cada ciclo de scan
    llama `on_cycle_end()` para calcular métricas y loguear resumen.
    """

    def __init__(
        self,
        watchlist: MaturingWatchlist,
        *,
        enabled: bool = True,
        max_cycle_history: int = 20,
    ) -> None:
        self._wl = watchlist
        self._cycle = _CycleAccumulator()
        self._state = {
            "counters": dict(watchlist.counters),
            "drop_reasons": {},
            "total_captured": 0,
            "total_promoted": 0,
            "total_bars_age": 0,
            "maturation_rate": 0.0,
            "avg_maturation_bars": 0.0,
            "live_shadow_ratio": 0.0,
        }
        self.enabled = enabled
        self.max_cycle_history = max_cycle_history
        self.cycle_history: list[CycleSnapshot] = []

    # ── Eventos desde MaturingWatchlist hooks ──

    def on_capture(self, entry: MaturingEntry) -> None:
        """Registra una captura (upsert_young)."""
        if not self.enabled:
            return
        self._cycle.captured += 1
        log.debug("[MATURING-WATCHER] capture %s %s banda=%.5f", entry.asset, entry.direction, entry.band)

    def on_promote(self, entry: MaturingEntry, mode: str) -> None:
        """Registra una promoción (mark_promoted)."""
        if not self.enabled:
            return
        if mode == "live":
            self._cycle.promoted_live += 1
        else:
            self._cycle.promoted_shadow += 1
        self._state["total_bars_age"] += entry.bars_age
        self._state["total_promoted"] += 1
        log.info(
            "[MATURING-WATCHER] promote %s %s banda=%.5f mode=%s bars_age=%d",
            entry.asset, entry.direction, entry.band, mode, entry.bars_age,
        )

    def on_drop(self, entry: MaturingEntry, reason: str) -> None:
        """Registra un drop."""
        if not self.enabled:
            return
        self._cycle.dropped[reason] = self._cycle.dropped.get(reason, 0) + 1
        self._state["drop_reasons"][reason] = self._state["drop_reasons"].get(reason, 0) + 1
        log.info(
            "[MATURING-WATCHER] drop %s %s banda=%.5f reason=%s",
            entry.asset, entry.direction, entry.band, reason,
        )

    # ── Fin de ciclo ──

    def on_cycle_end(self) -> CycleSnapshot | None:
        """Cierra el ciclo actual, calcula métricas, resetea acumulador.

        Debe llamarse DESPUÉS de expire_stale() en el scan cycle.
        """
        if not self.enabled:
            return None

        active = list(self._wl.active())
        avg_age = sum(e.bars_age for e in active) / len(active) if active else 0.0

        snap = CycleSnapshot(
            ts=time.time(),
            captured=self._cycle.captured,
            promoted_live=self._cycle.promoted_live,
            promoted_shadow=self._cycle.promoted_shadow,
            dropped=dict(self._cycle.dropped),
            active_before=self._cycle.active_before,
            active_after=len(active),
            avg_bars_age=round(avg_age, 1),
            total_bars_age=sum(e.bars_age for e in active),
        )

        # Rolling FIFO
        self.cycle_history.append(snap)
        if len(self.cycle_history) > self.max_cycle_history:
            self.cycle_history.pop(0)

        # Métricas derivadas (rolling window)
        total_cap = sum(c.captured for c in self.cycle_history)
        total_pro = sum(c.promoted_live + c.promoted_shadow for c in self.cycle_history)
        total_shadow_pro = sum(c.promoted_shadow for c in self.cycle_history)
        self._state["maturation_rate"] = total_pro / max(total_cap, 1)
        self._state["live_shadow_ratio"] = (
            sum(c.promoted_live for c in self.cycle_history) / max(total_shadow_pro, 1)
        )
        self._state["avg_maturation_bars"] = (
            self._state["total_bars_age"] / max(self._state["total_promoted"], 1)
        )
        self._state["total_captured"] = total_cap
        self._state["total_promoted"] = total_pro
        # Sync counters from watchlist
        self._state["counters"] = dict(self._wl.counters)

        # Log resumen del ciclo
        total_drops = sum(snap.dropped.values())
        log.info(
            "[MATURING-WATCHER] cycle: +%d cap, +%d live, +%d shadow, "
            "%d drops, %d active, avg_age=%.1f, rate=%.1f%%",
            snap.captured, snap.promoted_live, snap.promoted_shadow,
            total_drops, snap.active_after, snap.avg_bars_age,
            self._state["maturation_rate"] * 100,
        )

        self._cycle.reset()
        return snap

    # ── API pública ──

    def snapshot(self) -> dict[str, Any]:
        """Snapshot para el Hub / logs."""
        return {
            "counters": dict(self._state["counters"]),
            "drop_reasons": dict(self._state["drop_reasons"]),
            "maturation_rate": round(self._state["maturation_rate"], 3),
            "avg_maturation_bars": round(self._state["avg_maturation_bars"], 1),
            "live_shadow_ratio": round(self._state["live_shadow_ratio"], 2),
            "active": len(self._wl.active()),
            "cycle_history": [
                {
                    "ts": c.ts,
                    "captured": c.captured,
                    "promoted_live": c.promoted_live,
                    "promoted_shadow": c.promoted_shadow,
                    "drops": c.dropped,
                    "active_after": c.active_after,
                    "avg_bars_age": c.avg_bars_age,
                }
                for c in self.cycle_history[-5:]
            ],
        }
