"""Tests de entry_sync.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from entry_sync import EntrySynchronizer


def _sync(max_lag: float = 0.3) -> EntrySynchronizer:
    return EntrySynchronizer(
        tf_1m=60,
        max_lag_sec=max_lag,
        reject_last_sec=2.0,
        sync_enabled=True,
        duration_sec=30,
    )


def test_compute_timing_accepts_on_time_entry():
    sync = _sync()
    candle_open = 1_000_000
    now = candle_open + 0.1

    timing = sync.compute_timing(candle_open, now)

    assert timing.ok is True
    assert timing.lag_sec == pytest.approx(0.1)
    assert timing.time_since_open_sec == pytest.approx(now % 60)
    assert timing.secs_to_close_sec == pytest.approx(60 - (now % 60))
    assert timing.decision == "SYNCED_1M_OPEN"


def test_compute_timing_rejects_late_entry():
    sync = _sync(max_lag=0.3)
    candle_open = 1_000_000
    now = candle_open + 0.5

    timing = sync.compute_timing(candle_open, now)

    assert timing.ok is False
    assert timing.lag_sec == pytest.approx(0.5)
    assert timing.decision == "REJECT_LATE_1M"


def test_compute_timing_when_sync_disabled():
    sync = EntrySynchronizer(sync_enabled=False)

    timing = sync.compute_timing(candle_open_ts=0, now=999.0)

    assert timing.ok is True
    assert timing.decision == "SYNC_DISABLED"
    assert timing.lag_sec == 0.0


@pytest.mark.asyncio
async def test_sync_and_validate_waits_for_open(monkeypatch):
    sync = _sync()
    calls: list[float] = []

    async def fake_sleep(sec: float) -> None:
        calls.append(sec)

    times = iter([1000.0, 1000.0, 1060.05])

    monkeypatch.setattr("entry_sync.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("entry_sync.time.time", lambda: next(times))

    timing = await sync.sync_and_validate()

    assert calls and calls[0] > 0
    assert timing.ok is True
    assert timing.decision == "SYNCED_1M_OPEN"


def test_log_order_timing_emits_fields(caplog):
    sync = _sync()
    timing = sync.compute_timing(1_000_000, 1_000_000 + 0.05)

    with caplog.at_level("INFO", logger="entry_sync"):
        sync.log_order_timing("EURUSD_otc", timing)

    assert "time_since_open" in caplog.text
    assert "secs_to_close" in caplog.text
    assert "EURUSD_otc" in caplog.text