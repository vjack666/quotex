"""T9 — backfill idempotente (fixture reducida): doble pasada, count estable."""
import sqlite3

from marketfeed.base import Event, KIND_CANDLE_CLOSED
from observador.observer import Observador
from observador.store import EpisodeStore

PIP = 1e-4

# un episodio Fase A completo + captura que se apaga (CaptureMonitor)
EPISODE_BODIES = (
    [0.001, -0.001] * 5
    + [0.001, 0.001, 0.01, 0.01, 0.001, 0.001, -0.001]
    + [-0.005] * 5
    + [2 * PIP, -2 * PIP] * 4 + [0.0] * 6
)

N_EPISODES = 3


def _synthetic_events():
    events, last_close, ts = [], 1.0, 0
    for _ in range(N_EPISODES):
        for body in EPISODE_BODIES:
            o = last_close
            c = o + body
            ts += 60
            last_close = c
            events.append(Event(
                kind=KIND_CANDLE_CLOSED, asset="EURUSD", ts=ts,
                payload={"timeframe": 60, "open": o, "high": max(o, c),
                         "low": min(o, c), "close": c},
                source="REPLAY:test",
            ))
    return events


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


def _counts(db_path):
    con = sqlite3.connect(db_path)
    evo = con.execute("SELECT COUNT(*) FROM episode_evolution").fetchone()[0]
    summ = con.execute("SELECT COUNT(*) FROM episode_summary").fetchone()[0]
    con.close()
    return evo, summ


def test_doble_pasada_no_duplica(tmp_path):
    db = str(tmp_path / "ep.db")
    store = EpisodeStore(db)
    events = _synthetic_events()

    r1 = Observador(FakeFeed(events), store).run()
    assert r1["episodes_closed"] == N_EPISODES
    n_ep_1 = store.count_episodes()
    evo_1, summ_1 = _counts(db)
    assert n_ep_1 == N_EPISODES
    assert evo_1 > 0 and summ_1 == N_EPISODES

    # segunda pasada (backfill) con Observador nuevo sobre el MISMO store
    r2 = Observador(FakeFeed(events), store).run()
    assert r2["episodes_closed"] == N_EPISODES  # re-vistos, no re-insertados

    assert store.count_episodes() == n_ep_1     # idéntico antes/después
    assert _counts(db) == (evo_1, summ_1)       # sin filas duplicadas
    store.close()
