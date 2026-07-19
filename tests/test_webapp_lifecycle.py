"""Unit tests for hub.process_lifecycle and test-mode bankroll isolation."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hub.process_lifecycle import (
    acquire_pid_lock,
    pid_is_alive,
    release_pid_lock,
    reset_cleanup_flag_for_tests,
    run_exit_cleanup,
)


@pytest.fixture(autouse=True)
def _reset_cleanup_flag():
    reset_cleanup_flag_for_tests()
    yield
    reset_cleanup_flag_for_tests()


def test_pid_is_alive_current_process():
    assert pid_is_alive(os.getpid()) is True


def test_pid_is_alive_invalid():
    assert pid_is_alive(0) is False
    assert pid_is_alive(-1) is False
    # Extremely high PID is almost certainly dead.
    assert pid_is_alive(2_000_000_000) is False


def test_acquire_and_release_pid_lock(tmp_path: Path):
    lock = tmp_path / "main.lock"
    assert acquire_pid_lock(lock) is True
    assert lock.exists()
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())
    release_pid_lock(lock)
    assert not lock.exists()


def test_stale_pid_lock_is_replaced(tmp_path: Path):
    lock = tmp_path / "main.lock"
    lock.write_text("1999999999", encoding="utf-8")  # dead PID
    assert acquire_pid_lock(lock) is True
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())
    release_pid_lock(lock)


def test_live_pid_lock_blocks_second_acquire(tmp_path: Path):
    lock = tmp_path / "main.lock"
    # Write our own PID first (simulates foreign holder that is alive).
    # acquire_pid_lock treats same PID as ours and replaces — use a mock.
    lock.write_text(str(os.getpid()), encoding="utf-8")
    with patch("hub.process_lifecycle.os.getpid", return_value=os.getpid() + 99999):
        # Foreign process sees our live PID → must refuse.
        assert acquire_pid_lock(lock) is False
    # Original lock still ours
    assert lock.read_text(encoding="utf-8").strip() == str(os.getpid())
    release_pid_lock(lock)


def test_run_exit_cleanup_kills_browser_first():
    order: list[str] = []

    def kill_browser():
        order.append("browser")

    async def stop_bot():
        order.append("bot")

    run_exit_cleanup(kill_browser=kill_browser, stop_bot_coro_or_fn=stop_bot, timeout_sec=1.0)
    assert order == ["browser", "bot"]


def test_run_exit_cleanup_does_not_hang_on_slow_shutdown():
    async def slow_shutdown():
        await asyncio.sleep(30)

    t0 = time.monotonic()
    run_exit_cleanup(
        kill_browser=lambda: None,
        stop_bot_coro_or_fn=slow_shutdown,
        timeout_sec=0.3,
    )
    elapsed = time.monotonic() - t0
    assert elapsed < 2.0, f"cleanup hung for {elapsed:.2f}s"


def test_run_exit_cleanup_idempotent():
    calls = {"n": 0}

    def kill():
        calls["n"] += 1

    run_exit_cleanup(kill_browser=kill, timeout_sec=0.5)
    run_exit_cleanup(kill_browser=kill, timeout_sec=0.5)
    assert calls["n"] == 1


def test_hydrate_skipped_in_test_mode(monkeypatch):
    """Under test mode, hub bankroll min_payout=90 must not force MIN_PAYOUT."""
    import config as cfg

    # Defaults after conftest QUOTEX_TEST_MODE=1
    assert cfg._in_test_mode() is True
    baseline = cfg.MIN_PAYOUT

    monkeypatch.setattr(
        "hub_bankroll_store.load_bankroll",
        lambda: {
            "min_payout": 90,
            "massaniello_ops": 99,
            "massaniello_wins": 50,
            "massaniello_virtual_capital": 9999.0,
            "session_max_min": 999,
        },
    )
    # Re-run hydrate while still in test mode — must no-op.
    cfg._hydrate_bankroll_from_web()
    assert cfg.MIN_PAYOUT == baseline
    assert cfg.MIN_PAYOUT != 90 or baseline == 90  # only equal if baseline already 90


def test_hydrate_applies_when_not_in_test_mode(monkeypatch):
    """When test isolation is off, bankroll min_payout is applied."""
    import config as cfg

    monkeypatch.delenv("QUOTEX_TEST_MODE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    # Force _in_test_mode false even if pytest is in sys.modules
    monkeypatch.setattr(cfg, "_in_test_mode", lambda: False)

    orig_min = cfg.MIN_PAYOUT
    orig_a = cfg.STRAT_A_MIN_PAYOUT
    orig_f = cfg.STRAT_F_MIN_PAYOUT
    monkeypatch.setattr(
        "hub_bankroll_store.load_bankroll",
        lambda: {"min_payout": 91},
    )
    try:
        cfg._hydrate_bankroll_from_web()
        assert cfg.MIN_PAYOUT == 91
        assert cfg.STRAT_F_MIN_PAYOUT == 91
        assert cfg.STRAT_A_MIN_PAYOUT == 91
    finally:
        cfg.MIN_PAYOUT = orig_min
        cfg.STRAT_A_MIN_PAYOUT = orig_a
        cfg.STRAT_F_MIN_PAYOUT = orig_f
