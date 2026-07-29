"""T8 — Observer Fase B: captura post-RESOLUTION (CaptureMonitor vs natural)."""
import sqlite3

from marketfeed.base import Event, KIND_CANDLE_CLOSED
from observador.observer import Observador
from observador.store import EpisodeStore

# Fase A: quiet(10) + expansión + presión + freno + transición → REBOUND
BODIES_FASE_A = (
    [0.001, -0.001] * 5
    + [0.001, 0.001, 0.01, 0.01, 0.001, 0.001, -0.001]
    + [-0.005] * 5
)

PIP = 1e-4


def _events_from_bodies(bodies, ts0=0, step=60, start_close=1.0):
    events, last_close, ts = [], start_close, ts0
    for body in bodies:
        o = last_close
        c = o + body
        ts += step
        last_close = c
        events.append(Event(
            kind=KIND_CANDLE_CLOSED, asset="EURUSD", ts=ts,
            payload={"timeframe": 60, "open": o, "high": max(o, c),
                     "low": min(o, c), "close": c},
            source="REPLAY:test",
        ))
    return events, last_close, ts


class FakeFeed:
    def __init__(self, events):
        self._events = list(events)
        self._i = 0
        self._now = 0.0

    def next_event(self):
        if self._i >= len(self._events):
            return None
        e = self._events[self._i]
        self._i += 1
        self._now = e.ts
        return e

    def now(self):
        return self._now


def _capture_bodies():
    """~15 barras vivas (±2 pips alternando) + 5 quietas → CaptureMonitor."""
    return [2 * PIP, -2 * PIP] * 7 + [0.0] * 6


def _natural_bodies():
    """Tras RESOLUTION: nueva expansión alcista sostenida → NEW_PRESSURE."""
    return [0.01] * 8


def test_cierra_por_capture_monitor(tmp_path):
    store = EpisodeStore(str(tmp_path / "ep.db"))
    bodies = BODIES_FASE_A + _capture_bodies()
    events, _, _ = _events_from_bodies(bodies)
    result = Observador(FakeFeed(events), store).run()
    assert result["episodes_closed"] == 1

    ep = store.get_episode("EURUSD", 13 * 60, "REPLAY:test")
    assert ep is not None
    evo = store.get_evolution(ep["id"])
    # la traza sigue muchas barras después de RESOLUTION (Fase A duró 22 velas
    # desde ts0; el writer arranca en EXPANSION vela 13 → 10 velas Fase A)
    assert len(evo) > 10 + 10  # ~20 barras de captura extra
    s = store.get_summary(ep["id"])
    assert s is not None
    assert s["finished"] == 0
    assert s["capture_limit"] == 1
    assert s["end_reason"] is None
    assert s["duration_bars"] == len(evo)
    assert s["episode_type"] == "REBOUND"


def test_cierra_por_fin_natural_new_pressure(tmp_path):
    store = EpisodeStore(str(tmp_path / "ep.db"))
    bodies = BODIES_FASE_A + _natural_bodies()
    events, _, _ = _events_from_bodies(bodies)
    Observador(FakeFeed(events), store).run()

    ep = store.get_episode("EURUSD", 13 * 60, "REPLAY:test")
    assert ep is not None
    s = store.get_summary(ep["id"])
    assert s is not None
    assert s["finished"] == 1
    assert s["end_reason"] == "NEW_PRESSURE"
    assert s["capture_limit"] == 0
    assert s["end_confidence"] is not None

    # episode_version registrada
    con = sqlite3.connect(str(tmp_path / "ep.db"))
    row = con.execute(
        "SELECT vars_version, summary_version FROM episode_version "
        "WHERE episode_id=?", (ep["id"],)).fetchone()
    con.close()
    assert row == ("vars_v1", "summary_v1")
