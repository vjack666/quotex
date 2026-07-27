"""Tests T4/T5/T6 — ReplayFeed (Market Replay Engine)."""
from __future__ import annotations

import json

import pytest

from marketfeed.base import Event, KIND_CANDLE_CLOSED
from marketfeed.replay import ReplayFeed


class FakeSource:
    """Fuente fake in-line que implementa Source."""

    def __init__(self, events):
        self._events = list(events)

    def iter_events(self):
        return iter(self._events)

    def quality_report(self):
        return {"served": len(self._events), "discarded": 0, "gaps": 0}


def candle(asset, ts, tf=60):
    return Event(
        kind=KIND_CANDLE_CLOSED,
        asset=asset,
        ts=ts,
        payload={"timeframe": tf, "open": 1, "high": 1, "low": 1, "close": 1},
        source="REPLAY:test",
    )


class SleepSpy:
    def __init__(self):
        self.calls = []

    def __call__(self, secs):
        self.calls.append(secs)


# (a) aritmética del sleep
def test_speed_100_sleep_exact():
    spy = SleepSpy()
    feed = ReplayFeed([FakeSource([candle("EURUSD", 1000.0), candle("EURUSD", 1060.0)])],
                      speed=100, sleep_fn=spy)
    e1 = feed.next_event()
    e2 = feed.next_event()
    assert e1.ts == 1000.0 and e2.ts == 1060.0
    # 60 / 100 = 0.6, verificado
    assert 60.0 / 100 == 0.6
    assert spy.calls == [0.6]


# (b) MAX → 0 sleeps
def test_speed_max_no_sleep():
    spy = SleepSpy()
    feed = ReplayFeed([FakeSource([candle("EURUSD", 1000.0), candle("EURUSD", 1060.0)])],
                      speed="MAX", sleep_fn=spy)
    while feed.next_event() is not None:
        pass
    assert spy.calls == []


# (c) merge determinista
def test_merge_two_sources_ordered_deterministic():
    s1 = FakeSource([candle("EURUSD", 1000.0), candle("EURUSD", 1120.0)])
    s2 = FakeSource([candle("AUDCAD", 1000.0), candle("AUDCAD", 1060.0)])

    def run():
        feed = ReplayFeed([s1, s2], speed="MAX", sleep_fn=SleepSpy())
        out = []
        while True:
            ev = feed.next_event()
            if ev is None:
                break
            out.append((ev.ts, ev.asset))
        return out

    out1, out2 = run(), run()
    assert out1 == out2  # determinista
    ts_list = [t for t, _ in out1]
    assert ts_list == sorted(ts_list)  # no-decreciente
    # desempate por asset en ts=1000: AUDCAD antes que EURUSD
    assert out1[0] == (1000.0, "AUDCAD")
    assert out1[1] == (1000.0, "EURUSD")


# (d) now() == max ts consumido
def test_now_tracks_max_consumed():
    feed = ReplayFeed([FakeSource([candle("E", 1.0), candle("E", 2.0), candle("E", 5.0)])],
                      sleep_fn=SleepSpy())
    seen = []
    while True:
        ev = feed.next_event()
        if ev is None:
            break
        seen.append(ev.ts)
        assert feed.now() == max(seen)


# (e) adversarial: API pública no lee por delante del cursor
def test_adversarial_no_future_leak():
    WHITELIST = {"next_event", "now", "pause", "resume", "step", "seek",
                 "bookmark", "export_bookmarks", "set_speed"}
    feed = ReplayFeed([FakeSource([candle("E", 10.0), candle("E", 20.0), candle("E", 30.0)])],
                      sleep_fn=SleepSpy())
    public = {n for n in dir(feed) if not n.startswith("_") and callable(getattr(feed, n))}
    assert public <= WHITELIST
    delivered = []
    for _ in range(3):
        ev = feed.next_event()
        delivered.append(ev)
        assert all(e.ts <= feed.now() for e in delivered)
    assert feed.now() == delivered[-1].ts


# (f) pause / step / resume
def test_pause_step_resume():
    feed = ReplayFeed([FakeSource([candle("E", 1.0), candle("E", 2.0), candle("E", 3.0)])],
                      sleep_fn=SleepSpy())
    feed.pause()
    assert feed.next_event() is None
    assert feed.now() == 0.0  # no avanzó
    ev = feed.step()
    assert ev is not None and ev.ts == 1.0 and feed.now() == 1.0
    assert feed.next_event() is None  # sigue en pausa
    feed.resume()
    ev2 = feed.next_event()
    assert ev2.ts == 2.0


# (g) seek al medio, sin sleeps
def test_seek_middle_no_sleep_no_future():
    spy = SleepSpy()
    events = [candle("E", 100.0), candle("E", 160.0), candle("E", 220.0), candle("E", 280.0)]
    feed = ReplayFeed([FakeSource(events)], speed=1, sleep_fn=spy)
    feed.seek(160.0)
    assert spy.calls == []  # cero sleeps durante seek
    assert feed.now() == 160.0
    nxt = feed.next_event()
    assert nxt.ts == 220.0


# (h) bookmarks JSON
def test_bookmarks_export(tmp_path):
    feed = ReplayFeed([FakeSource([candle("E", 5.0), candle("E", 6.0)])], sleep_fn=SleepSpy())
    feed.next_event()
    feed.bookmark("primera")
    feed.next_event()
    feed.bookmark("segunda")
    out = tmp_path / "bm.json"
    feed.export_bookmarks(str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == [{"ts": 5.0, "nota": "primera"}, {"ts": 6.0, "nota": "segunda"}]


def test_set_speed_hot():
    spy = SleepSpy()
    feed = ReplayFeed([FakeSource([candle("E", 0.0), candle("E", 60.0), candle("E", 120.0)])],
                      speed="MAX", sleep_fn=spy)
    feed.next_event()
    feed.next_event()
    assert spy.calls == []
    feed.set_speed(10)
    feed.next_event()
    assert spy.calls == [6.0]
    with pytest.raises(ValueError):
        feed.set_speed(0)
