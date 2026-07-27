"""Tests T5 — Observador sobre feed fake con velas sintéticas de 2 assets."""
from marketfeed.base import Event, KIND_CANDLE_CLOSED, KIND_FEED_GAP
from observador.observer import Observador
from observador.store import EpisodeStore


# --- secuencia sintética (adaptada de tests/test_observador_state_machine.py):
# quiet(10) + 3 alcistas (EXPANSION) + 1 (PRESSURE) + 2 lentas (BRAKE)
# + 1 contraria (TRANSITION) + 5 contrarias fuertes (RESOLUTION=REBOUND)
BODIES = (
    [0.001, -0.001] * 5
    + [0.001, 0.001, 0.01, 0.01, 0.001, 0.001, -0.001]
    + [-0.005] * 5
)


def build_candles(ts0=0, step=60):
    candles, last_close, ts = [], 1.0, ts0
    for body in BODIES:
        o = last_close
        c = o + body
        ts += step
        last_close = c
        candles.append({"ts": ts, "open": o, "high": max(o, c),
                        "low": min(o, c), "close": c})
    return candles


def candle_event(asset, c, source="REPLAY:test"):
    return Event(
        kind=KIND_CANDLE_CLOSED, asset=asset, ts=c["ts"],
        payload={"timeframe": 60, "open": c["open"], "high": c["high"],
                 "low": c["low"], "close": c["close"]},
        source=source,
    )


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


def interleaved_events(with_gap=False):
    ca = build_candles(ts0=0)
    cb = build_candles(ts0=1)  # offset 1s para orden total
    events = []
    for a, b in zip(ca, cb):
        events.append(candle_event("EURUSD", a))
        events.append(candle_event("GBPUSD", b))
    if with_gap:
        # gap a mitad del episodio de EURUSD (tras la vela 15 = ya en PRESSURE)
        idx = 15 * 2
        events.insert(idx, Event(kind=KIND_FEED_GAP, asset="EURUSD",
                                 ts=ca[14]["ts"] + 1,
                                 payload={"ts_desde": 0, "ts_hasta": 0},
                                 source="REPLAY:test"))
    return events


def test_two_assets_two_episodes(tmp_path):
    store = EpisodeStore(str(tmp_path / "ep.db"))
    feed = FakeFeed(interleaved_events())
    obs = Observador(feed, store)
    summary = obs.run()

    assert summary["episodes_closed"] == 2
    assert summary["episodes_open"] == 0
    assert summary["events_consumed"] == len(BODIES) * 2
    assert store.count_episodes() == 2

    for asset, ts0 in (("EURUSD", 0), ("GBPUSD", 1)):
        # EXPANSION en la vela 13 (ts = 13*60 + offset)
        ep = store.get_episode(asset, 13 * 60 + ts0, "REPLAY:test")
        assert ep is not None
        assert ep["state_final"] == "RESOLUTION"
        assert ep["resolution_type"] == "REBOUND"
        assert ep["formula_version"] == "transitions_v1"
        assert ep["confidence"] == 1.0
        assert ep["ts_close"] > ep["ts_open"]
        assert len(ep["pressure_points"]) > 0
        state_names = [s["state"] for s in ep["states"]]
        assert state_names == ["EXPANSION", "PRESSURE", "BRAKE",
                               "TRANSITION", "RESOLUTION"]
        for s in ep["states"]:
            assert s["trigger_formula"] in ("quiet_exit_v1", "transitions_v1")


def test_feed_gap_degrades_confidence(tmp_path):
    store = EpisodeStore(str(tmp_path / "ep.db"))
    obs = Observador(FakeFeed(interleaved_events(with_gap=True)), store)
    obs.run()
    ep = store.get_episode("EURUSD", 13 * 60, "REPLAY:test")
    assert ep is not None
    assert ep["confidence"] < 1.0
    assert ep["confidence"] == 0.5
    assert "GAP" in [s["state"] for s in ep["states"]]
    # GBPUSD no afectada por el gap
    ep_b = store.get_episode("GBPUSD", 13 * 60 + 1, "REPLAY:test")
    assert ep_b["confidence"] == 1.0


def test_other_timeframes_ignored(tmp_path):
    store = EpisodeStore(str(tmp_path / "ep.db"))
    events = [Event(kind=KIND_CANDLE_CLOSED, asset="EURUSD", ts=60.0 * i,
                    payload={"timeframe": 300, "open": 1, "high": 1,
                             "low": 1, "close": 1}, source="REPLAY:test")
              for i in range(1, 30)]
    summary = Observador(FakeFeed(events), store).run()
    assert summary["events_consumed"] == 29
    assert summary["episodes_closed"] == 0
    assert store.count_episodes() == 0


def test_max_events_limits_consumption(tmp_path):
    store = EpisodeStore(str(tmp_path / "ep.db"))
    summary = Observador(FakeFeed(interleaved_events()), store).run(max_events=5)
    assert summary["events_consumed"] == 5
