"""Tests for quiet inline countdown (no per-second log spam)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from loop_utils import sleep_with_inline_countdown


@pytest.mark.asyncio
async def test_countdown_logs_once_and_returns_false(monkeypatch):
    """Normal wait: one start log.info, no spam; returns False."""
    mono = {"t": 1000.0}

    def fake_monotonic():
        return mono["t"]

    async def fake_sleep(dt):
        mono["t"] += float(dt)

    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.time.monotonic", fake_monotonic)
    monkeypatch.setattr("loop_utils.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("loop_utils.log", log_mock)
    monkeypatch.setattr("loop_utils.sys.stdout.isatty", lambda: False)

    aborted = await sleep_with_inline_countdown(5.0, "Próximo escaneo")

    assert aborted is False
    assert log_mock.info.call_count == 1
    args, _kwargs = log_mock.info.call_args
    assert "wait=%ss" in args[0]
    assert args[1] == "Próximo escaneo"
    assert args[2] == 5


@pytest.mark.asyncio
async def test_countdown_abort_logs_interrupt_once(monkeypatch):
    """Abort path: start log + one interrupt log; returns True."""
    mono = {"t": 1000.0}
    calls = {"n": 0}

    def fake_monotonic():
        return mono["t"]

    async def fake_sleep(dt):
        mono["t"] += float(dt)

    def should_abort():
        calls["n"] += 1
        return calls["n"] >= 2

    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.time.monotonic", fake_monotonic)
    monkeypatch.setattr("loop_utils.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("loop_utils.log", log_mock)
    monkeypatch.setattr("loop_utils.sys.stdout.isatty", lambda: False)

    aborted = await sleep_with_inline_countdown(
        10.0, "Próximo escaneo", should_abort=should_abort
    )

    assert aborted is True
    assert log_mock.info.call_count == 2
    start_msg = log_mock.info.call_args_list[0][0][0]
    abort_msg = log_mock.info.call_args_list[1][0][0]
    assert "wait=%ss" in start_msg
    assert "interrumpido" in abort_msg


@pytest.mark.asyncio
async def test_countdown_zero_wait_no_log(monkeypatch):
    """Zero/negative wait returns immediately without logging."""
    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.log", log_mock)

    aborted = await sleep_with_inline_countdown(0.0, "noop")
    assert aborted is False
    assert log_mock.info.call_count == 0


@pytest.mark.asyncio
async def test_countdown_tty_overwrites_same_line(monkeypatch):
    """TTY path writes clock updates with CR (same line), not new lines."""
    from io import StringIO

    mono = {"t": 1000.0}
    writes: list[str] = []

    class FakeTTY(StringIO):
        def isatty(self) -> bool:
            return True

        def write(self, s: str) -> int:
            writes.append(s)
            return super().write(s)

    fake = FakeTTY()

    def fake_monotonic():
        return mono["t"]

    async def fake_sleep(dt):
        mono["t"] += float(dt)

    log_mock = MagicMock()
    monkeypatch.setattr("loop_utils.time.monotonic", fake_monotonic)
    monkeypatch.setattr("loop_utils.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("loop_utils.log", log_mock)
    monkeypatch.setattr("loop_utils._countdown_stream", lambda: fake)
    monkeypatch.setattr("loop_utils._VT_ENABLED", True, raising=False)
    # Force ANSI path used in production after VT enable.
    monkeypatch.setattr("loop_utils._enable_windows_vt", lambda _s: None)

    import loop_utils as lu

    monkeypatch.setattr(lu, "_VT_ENABLED", True)

    aborted = await sleep_with_inline_countdown(3.0, "Sincronizando open vela 5m")
    assert aborted is False
    # Durable log still once only.
    assert log_mock.info.call_count == 1
    # Live ticks must use CR overwrite, never bare newlines as separators.
    live = [w for w in writes if "Sincronizando" in w]
    assert len(live) >= 2
    assert all(w.startswith("\r") for w in live)
    assert all("\n" not in w for w in live)
