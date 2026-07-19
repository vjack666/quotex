"""Tests de entry_sync.py — entry TF (default 5m)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from entry_sync import EntrySynchronizer


def _sync(max_lag: float = 0.3, tf_sec: int = 300) -> EntrySynchronizer:
    return EntrySynchronizer(
        tf_sec=tf_sec,
        max_lag_sec=max_lag,
        reject_last_sec=2.0,
        sync_enabled=True,
        duration_sec=300,
    )


def test_compute_timing_accepts_on_time_entry():
    sync = _sync()
    candle_open = 1_000_000  # multiple of 300? 1000000 % 300 = 100 — use aligned open
    candle_open = 1_000_200  # 1000200 % 300 == 0
    now = candle_open + 0.1

    timing = sync.compute_timing(candle_open, now)

    assert timing.ok is True
    assert timing.lag_sec == pytest.approx(0.1)
    assert timing.time_since_open_sec == pytest.approx(now % 300)
    assert timing.secs_to_close_sec == pytest.approx(300 - (now % 300))
    assert timing.decision == "SYNCED_ENTRY_OPEN"


def test_compute_timing_rejects_late_entry():
    sync = _sync(max_lag=0.3)
    candle_open = 1_000_200
    now = candle_open + 0.5

    timing = sync.compute_timing(candle_open, now)

    assert timing.ok is False
    assert timing.lag_sec == pytest.approx(0.5)
    assert timing.decision == "REJECT_LATE_ENTRY"


def test_compute_timing_when_sync_disabled():
    sync = EntrySynchronizer(sync_enabled=False)

    timing = sync.compute_timing(candle_open_ts=0, now=999.0)

    assert timing.ok is True
    assert timing.decision == "SYNC_DISABLED"
    assert timing.lag_sec == 0.0


@pytest.mark.asyncio
async def test_sync_and_validate_waits_for_open(monkeypatch):
    sync = _sync(tf_sec=300)
    calls: list[tuple[float, str]] = []

    async def fake_countdown(wait_sec: float, label: str, **kwargs) -> bool:
        calls.append((float(wait_sec), label))
        return False

    # now=1000 → phase = 1000 % 300 = 100 → next open = 1200, wait ~200
    # after sleep, send_ts near open with small lag
    times = iter([1000.0, 1200.05])

    monkeypatch.setattr("loop_utils.sleep_with_inline_countdown", fake_countdown)
    monkeypatch.setattr("entry_sync.time.time", lambda: next(times))

    timing = await sync.sync_and_validate()

    assert calls and calls[0][0] == pytest.approx(200.0)
    assert "300" in calls[0][1]
    assert timing.ok is True
    assert timing.decision == "SYNCED_ENTRY_OPEN"


@pytest.mark.asyncio
async def test_sync_and_validate_exact_open_phase_zero_no_wait(monkeypatch):
    """At exact candle open (phase==0), wait 0 and use current open — do not jump next."""
    sync = _sync(tf_sec=300)
    calls: list[float] = []

    async def fake_countdown(wait_sec: float, label: str, **kwargs) -> bool:
        calls.append(float(wait_sec))
        return False

    # 1200 % 300 == 0 → already at open
    open_ts = 1200.0
    times = iter([open_ts, open_ts + 0.05])

    monkeypatch.setattr("loop_utils.sleep_with_inline_countdown", fake_countdown)
    monkeypatch.setattr("entry_sync.time.time", lambda: next(times))

    timing = await sync.sync_and_validate()

    assert calls == []  # no sleep when phase == 0
    assert timing.ok is True
    assert timing.decision == "SYNCED_ENTRY_OPEN"
    assert timing.lag_sec == pytest.approx(0.05)


def test_default_tf_is_5m():
    sync = EntrySynchronizer(sync_enabled=False)
    assert sync.tf_sec == 300


def test_log_order_timing_emits_fields(caplog):
    sync = _sync()
    candle_open = 1_000_200
    timing = sync.compute_timing(candle_open, candle_open + 0.05)

    with caplog.at_level("INFO", logger="entry_sync"):
        sync.log_order_timing("EURUSD_otc", timing)

    assert "time_since_open" in caplog.text
    assert "secs_to_close" in caplog.text
    assert "EURUSD_otc" in caplog.text
