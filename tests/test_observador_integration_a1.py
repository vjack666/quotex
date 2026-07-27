"""Tests T6/T7 — Observador vía ReplayFeed real y LiveFeed stub; idempotencia."""
from marketfeed.live_stub import LiveFeed
from marketfeed.replay import ReplayFeed
from observador.observer import Observador
from observador.store import EpisodeStore

from test_observador_observer import build_candles, candle_event


class FakeSource:
    def __init__(self, events):
        self._events = list(events)

    def iter_events(self):
        return iter(self._events)

    def quality_report(self):
        return {"served": len(self._events), "discarded": 0, "gaps": 0}


def make_events():
    ca = build_candles(ts0=0)
    cb = build_candles(ts0=1)
    events = []
    for a, b in zip(ca, cb):
        events.append(candle_event("EURUSD", a))
        events.append(candle_event("GBPUSD", b))
    return events


def episode_keys(store):
    rows = store._conn.execute(
        "SELECT asset, ts_open, resolution_type FROM episodes ORDER BY asset"
    ).fetchall()
    return [(r["asset"], r["ts_open"], r["resolution_type"]) for r in rows]


def test_replay_vs_live_same_episodes(tmp_path):
    events = make_events()

    # (a) ReplayFeed real a speed MAX
    store_r = EpisodeStore(str(tmp_path / "replay.db"))
    feed_r = ReplayFeed([FakeSource(events)], speed="MAX")
    Observador(feed_r, store_r).run()

    # (b) LiveFeed con get_candles fake que se agota
    candles_by_asset = {"EURUSD": build_candles(ts0=0),
                        "GBPUSD": build_candles(ts0=1)}
    served = {"EURUSD": False, "GBPUSD": False}

    def get_candles(asset, timeframe):
        if served[asset]:
            return []
        served[asset] = True
        return candles_by_asset[asset]

    store_l = EpisodeStore(str(tmp_path / "live.db"))
    feed_l = LiveFeed(get_candles, ["EURUSD", "GBPUSD"], timeframe=60)
    Observador(feed_l, store_l).run()

    assert store_r.count_episodes() == store_l.count_episodes() == 2
    keys_r = episode_keys(store_r)
    keys_l = episode_keys(store_l)
    assert [(a, t, rt) for a, t, rt in keys_r] == \
           [(a, t, rt) for a, t, rt in keys_l]


def test_replay_idempotent_second_pass(tmp_path):
    """T7 — dos pasadas del mismo replay sobre el MISMO store (R4.3)."""
    events = make_events()
    store = EpisodeStore(str(tmp_path / "idem.db"))

    Observador(ReplayFeed([FakeSource(events)], speed="MAX"), store).run()
    count1 = store.count_episodes()
    assert count1 == 2

    Observador(ReplayFeed([FakeSource(events)], speed="MAX"), store).run()
    assert store.count_episodes() == count1
