"""Tests MarketRecorder — Observador (Capa 2).

FeedMock local sintético (no importa el bot). Timestamps fijos.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd
import pytest

from marketfeed.base import Event, MarketFeed
from marketfeed.recorder import MarketRecorder

T0 = 1_753_000_000.0  # timestamp sintético fijo
TF = 900  # M15


def make_candles(n: int, asset: str = "EURUSD_otc") -> List[Event]:
    evs = []
    for i in range(n):
        px = 1.1000 + i * 0.0010
        evs.append(
            Event(
                kind="CANDLE_CLOSED",
                asset=asset,
                ts=T0 + i * TF,
                payload={
                    "timeframe": TF,
                    "open": px,
                    "high": px + 0.0005,
                    "low": px - 0.0005,
                    "close": px + 0.0002,
                    "volume": 10.0 + i,
                    "tick_volume": 100 + i,
                },
                source="TEST:mock",
            )
        )
    return evs


class FeedMock:
    """Feed mínimo sintético que emite eventos en orden."""

    def __init__(self, events: List[Event]) -> None:
        self._events = list(events)
        self._i = 0
        self._now = 0.0

    def next_event(self) -> Optional[Event]:
        if self._i >= len(self._events):
            return None
        ev = self._events[self._i]
        self._i += 1
        self._now = ev.ts
        return ev

    def now(self) -> float:
        return self._now


class ExplodingFeed(FeedMock):
    """Adversarial: lanza si se piden más eventos que los realmente ocurridos."""

    def __init__(self, events: List[Event], allowed_calls: int) -> None:
        super().__init__(events)
        self._allowed = allowed_calls
        self.calls = 0

    def next_event(self) -> Optional[Event]:
        self.calls += 1
        if self.calls > self._allowed:
            raise AssertionError("REGLA SAGRADA VIOLADA: se intentó leer el futuro")
        return super().next_event()


def test_recorder_implements_marketfeed(tmp_path):
    rec = MarketRecorder(FeedMock([]), tmp_path / "out.parquet")
    assert isinstance(rec, MarketFeed)


def test_records_candles_with_schema(tmp_path):
    out = tmp_path / "out.parquet"
    rec = MarketRecorder(FeedMock(make_candles(5)), out)
    while rec.next_event() is not None:
        pass
    rec.close()
    df = pd.read_parquet(out)
    assert list(df.columns) == [
        "time", "open", "high", "low", "close",
        "volume", "tick_volume", "asset", "tf", "kind",
    ]
    assert (df["kind"] == "CANDLE_CLOSED").all()
    assert (df["tf"] == TF).all()
    assert (df["asset"] == "EURUSD_otc").all()


def test_row_count_exact(tmp_path):
    n = 7
    out = tmp_path / "out.parquet"
    rec = MarketRecorder(FeedMock(make_candles(n)), out, buffer_size=3)
    while rec.next_event() is not None:
        pass
    rec.close()
    assert len(pd.read_parquet(out)) == n


def test_adversarial_never_reads_future(tmp_path):
    """Regla Sagrada: grabar k velas => exactamente k llamadas al feed."""
    n, k = 10, 4
    feed = ExplodingFeed(make_candles(n), allowed_calls=k)
    out = tmp_path / "out.parquet"
    rec = MarketRecorder(feed, out)
    for _ in range(k):
        assert rec.next_event() is not None
    rec.close()
    assert feed.calls == k  # ni una llamada extra: cero prefetch del futuro
    df = pd.read_parquet(out)
    assert len(df) == k  # solo se grabó lo consumido
    assert df["time"].max() <= rec.now()  # nada con ts > now()


def test_mock_feed_passthrough_and_values(tmp_path):
    """El consumidor recibe los mismos eventos (vivo == replay)."""
    events = make_candles(3)
    out = tmp_path / "out.parquet"
    rec = MarketRecorder(FeedMock(events), out)
    seen = []
    ev = rec.next_event()
    while ev is not None:
        seen.append(ev)
        ev = rec.next_event()
    rec.close()
    assert seen == events
    df = pd.read_parquet(out)
    assert df["time"].tolist() == [e.ts for e in events]
    assert df["close"].tolist() == pytest.approx(
        [e.payload["close"] for e in events]
    )


def test_non_candle_events_not_recorded(tmp_path):
    tick = Event(kind="TICK", asset="EURUSD_otc", ts=T0, payload={"price": 1.1})
    gap = Event(kind="FEED_GAP", asset="EURUSD_otc", ts=T0 + 1,
                payload={"ts_desde": T0, "ts_hasta": T0 + 1})
    candle = make_candles(1)[0]
    out = tmp_path / "out.parquet"
    with MarketRecorder(FeedMock([tick, gap, candle]), out) as rec:
        while rec.next_event() is not None:
            pass
    df = pd.read_parquet(out)
    assert len(df) == 1
    assert df.iloc[0]["kind"] == "CANDLE_CLOSED"
