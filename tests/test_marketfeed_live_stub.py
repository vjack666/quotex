"""T7 — LiveFeed stub con get_candles inyectado (R1.2)."""
from marketfeed.base import KIND_CANDLE_CLOSED, MarketFeed
from marketfeed.live_stub import LiveFeed

CANDLES = {
    "EURUSD": [
        {"ts": 60, "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1},
        {"ts": 120, "open": 1.1, "high": 1.3, "low": 1.0, "close": 1.2},
    ],
    "GBPUSD": [
        {"ts": 60, "open": 2.0, "high": 2.2, "low": 1.9, "close": 2.1},
    ],
}


def fake_get_candles(asset, timeframe):
    assert timeframe == 60
    return CANDLES.get(asset, [])


def drain(feed, max_iter=20):
    out = []
    for _ in range(max_iter):
        e = feed.next_event()
        if e is None:
            break
        out.append(e)
    return out


def test_eventos_bien_formados_y_source():
    feed = LiveFeed(fake_get_candles, ["EURUSD", "GBPUSD"], timeframe=60)
    events = drain(feed)
    assert len(events) == 3
    for e in events:
        assert e.kind == KIND_CANDLE_CLOSED
        assert e.source == "LIVE:quotex"
        assert e.payload["timeframe"] == 60
        assert isinstance(e.ts, float)
        assert {"open", "high", "low", "close"} <= set(e.payload)


def test_dedup_de_velas_ya_vistas():
    feed = LiveFeed(fake_get_candles, ["EURUSD", "GBPUSD"], timeframe=60)
    first = drain(feed)
    assert len(first) == 3
    # segunda pasada: mismas velas -> nada nuevo
    assert feed.next_event() is None
    # nueva vela aparece -> se emite solo esa
    CANDLES["EURUSD"].append(
        {"ts": 180, "open": 1.2, "high": 1.4, "low": 1.1, "close": 1.3})
    try:
        nuevos = drain(feed)
        assert [e.ts for e in nuevos] == [180.0]
        assert nuevos[0].asset == "EURUSD"
    finally:
        CANDLES["EURUSD"].pop()


def test_es_marketfeed_y_now_flotante():
    feed = LiveFeed(fake_get_candles, ["EURUSD"])
    assert isinstance(feed, MarketFeed)
    assert isinstance(feed.now(), float)
