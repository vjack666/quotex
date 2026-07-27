"""Observador Fase A — consume MarketFeed y persiste episodios (T5).

Regla Sagrada: JAMÁS relojes de pared. El único reloj es
feed.now() y los ts de los eventos del feed.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from marketfeed.base import KIND_CANDLE_CLOSED, KIND_FEED_GAP, MarketFeed
from observador.pressure import pressure_point
from observador.state_machine import (
    EXPANSION,
    QUIET,
    RESOLUTION,
    ROLLING_WINDOW,
    TRANSITIONS_VERSION,
    EpisodeStateMachine,
)
from observador.store import EpisodeStore

M1 = 60
GAP_CONFIDENCE_FACTOR = 0.5
GAP_CONFIDENCE_MIN = 0.1
GAP_FORMULA = "gap_v1"


class _AssetContext:
    """Estado por asset: máquina, ventana y episodio activo."""

    def __init__(self, asset: str) -> None:
        self.asset = asset
        self.sm = EpisodeStateMachine(asset)
        self.window: deque[dict] = deque(maxlen=ROLLING_WINDOW)
        self.reset_episode()

    def reset_episode(self) -> None:
        self.states: list[dict] = []
        self.pressure_points: list[dict] = []
        self.confidence = 1.0
        self.ts_open: Optional[float] = None
        self.source: Optional[str] = None

    @property
    def episode_open(self) -> bool:
        return self.ts_open is not None


def _flatten_state(ev: dict) -> dict:
    trig = ev["trigger"]
    return {
        "state": ev["state_to"],
        "ts_enter": ev["ts"],
        "trigger_raw": trig.raw,
        "trigger_norm": trig.normalized,
        "trigger_confidence": trig.confidence,
        "trigger_formula": trig.formula_version,
    }


def _flatten_point(ts: float, point: dict) -> dict:
    adv = point["net_advance"]
    cont = point["continuity"]
    return {
        "ts": ts,
        "direction": point["direction"],
        "net_advance_raw": adv.raw,
        "net_advance_norm": adv.normalized,
        "continuity": cont.raw,
        "confidence": min(adv.confidence, cont.confidence),
        "formula_version": point["formula_version"],
    }


class Observador:
    """Consume eventos del feed, mantiene episodios y los persiste."""

    def __init__(
        self,
        feed: MarketFeed,
        store: EpisodeStore,
        source_label: Optional[str] = None,
    ) -> None:
        self._feed = feed
        self._store = store
        self._source_label = source_label
        self._contexts: dict[str, _AssetContext] = {}

    def _ctx(self, asset: str) -> _AssetContext:
        if asset not in self._contexts:
            self._contexts[asset] = _AssetContext(asset)
        return self._contexts[asset]

    def run(self, max_events: Optional[int] = None) -> dict:
        events_consumed = 0
        episodes_closed = 0
        while max_events is None or events_consumed < max_events:
            e = self._feed.next_event()
            if e is None:
                break
            events_consumed += 1
            if e.kind == KIND_FEED_GAP:
                ctx = self._ctx(e.asset)
                if ctx.episode_open:
                    ctx.confidence = max(
                        GAP_CONFIDENCE_MIN, ctx.confidence * GAP_CONFIDENCE_FACTOR
                    )
                    ctx.states.append({
                        "state": "GAP",
                        "ts_enter": e.ts,
                        "trigger_raw": GAP_CONFIDENCE_FACTOR,
                        "trigger_norm": GAP_CONFIDENCE_FACTOR,
                        "trigger_confidence": ctx.confidence,
                        "trigger_formula": GAP_FORMULA,
                    })
                continue
            if e.kind != KIND_CANDLE_CLOSED:
                continue
            if e.payload.get("timeframe") != M1:
                continue  # Fase A: solo M1

            ctx = self._ctx(e.asset)
            candle = {
                "ts": e.ts,
                "open": e.payload["open"],
                "high": e.payload["high"],
                "low": e.payload["low"],
                "close": e.payload["close"],
            }
            ctx.window.append(candle)
            transitions = ctx.sm.on_candle(candle)

            for ev in transitions:
                if ev["state_to"] == EXPANSION and ev["state_from"] == QUIET:
                    ctx.ts_open = ev["ts"]
                    ctx.source = e.source or (self._source_label or "")
                ctx.states.append(_flatten_state(ev))

            # pressure points: episodio activo con dirección conocida
            if (
                ctx.sm.state != QUIET
                and ctx.sm.direction is not None
                and len(ctx.window) >= 2
            ):
                point = pressure_point(list(ctx.window), ctx.sm.direction)
                ctx.pressure_points.append(_flatten_point(e.ts, point))

            resolved = [t for t in transitions if t["state_to"] == RESOLUTION]
            if resolved and ctx.episode_open:
                ev = resolved[-1]
                episode = {
                    "asset": ctx.asset,
                    "source": ctx.source
                    if ctx.source is not None
                    else (self._source_label or ""),
                    "ts_open": ctx.ts_open,
                    "ts_close": ev["ts"],
                    "state_final": RESOLUTION,
                    "resolution_type": ctx.sm.resolution_type,
                    "formula_version": TRANSITIONS_VERSION,
                    "confidence": ctx.confidence,
                    "states": list(ctx.states),
                    "pressure_points": list(ctx.pressure_points),
                }
                self._store.save_episode(episode)
                episodes_closed += 1
                # nueva máquina para el siguiente episodio
                ctx.sm = EpisodeStateMachine(ctx.asset)
                ctx.window.clear()
                ctx.reset_episode()

        episodes_open = sum(1 for c in self._contexts.values() if c.episode_open)
        return {
            "events_consumed": events_consumed,
            "episodes_closed": episodes_closed,
            "episodes_open": episodes_open,
        }
