"""T8/A1 — mismo consumidor contra dos implementaciones de MarketFeed.

R1.3: cambiar de feed = configuración, nunca código del consumidor.
R1.4: el consumidor JAMÁS usa time.time(); solo feed.now().

NOTA: usa un ReplayFeedFake in-line (el ReplayFeed real lo prueba T9).
"""
from typing import List, Optional

from marketfeed.base import Event, KIND_CANDLE_CLOSED, MarketFeed
from marketfeed.live_stub import LiveFeed

CANDLES = {
    "EURUSD": [
        {"ts": 60, "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1},
        {"ts": 120, "open": 1.1, "high": 1.3, "low": 1.0, "close": 1.25},
    ],
    "GBPUSD": [
        {"ts": 60, "open": 2.0, "high": 2.2, "low": 1.9, "close": 2.05},
        {"ts": 120, "open": 2.05, "high": 2.3, "low": 2.0, "close": 2.15},
        {"ts": 180, "open": 2.15, "high": 2.4, "low": 2.1, "close": 2.30},
    ],
}


class ReplayFeedFake:
    """MarketFeed mínimo sobre lista fija de Events. now() = ts del último consumido."""

    def __init__(self, events: List[Event]):
        self._events = sorted(events, key=lambda e: e.ts)
        self._i = 0
        self._now = self._events[0].ts if self._events else 0.0

    def next_event(self) -> Optional[Event]:
        if self._i >= len(self._events):
            return None
        e = self._events[self._i]
        self._i += 1
        self._now = e.ts
        return e

    def now(self) -> float:
        return self._now


class ObservadorDePrueba:
    """Consumidor de prueba: SOLO usa feed.next_event() y feed.now()."""

    def __init__(self, feed):
        self.feed = feed
        self.conteos = {}
        self.ultimo_close = {}
        self.ultimo_now = None

    def run(self):
        while True:
            e = self.feed.next_event()
            if e is None:
                break
            if e.kind == KIND_CANDLE_CLOSED:
                self.conteos[e.asset] = self.conteos.get(e.asset, 0) + 1
                self.ultimo_close[e.asset] = e.payload["close"]
            self.ultimo_now = self.feed.now()


def _events_replay() -> List[Event]:
    out = []
    for asset, candles in CANDLES.items():
        for c in candles:
            out.append(Event(kind=KIND_CANDLE_CLOSED, asset=asset,
                             ts=float(c["ts"]),
                             payload={"timeframe": 60, **c},
                             source="REPLAY:fake"))
    return out


def test_a1_mismo_consumidor_dos_feeds():
    replay = ReplayFeedFake(_events_replay())
    live = LiveFeed(lambda a, tf: CANDLES.get(a, []),
                    list(CANDLES.keys()), timeframe=60)

    assert isinstance(replay, MarketFeed)
    assert isinstance(live, MarketFeed)

    obs_r = ObservadorDePrueba(replay)
    obs_l = ObservadorDePrueba(live)
    obs_r.run()
    obs_l.run()

    assert obs_r.conteos == {"EURUSD": 2, "GBPUSD": 3}
    assert obs_l.conteos == obs_r.conteos
    assert obs_l.ultimo_close == obs_r.ultimo_close == {
        "EURUSD": 1.25, "GBPUSD": 2.30}
    # R1.4: ambos consumidores obtuvieron un now() del feed (no time.time()).
    assert obs_r.ultimo_now == 180.0  # ts del último evento consumido
    assert isinstance(obs_l.ultimo_now, float)
