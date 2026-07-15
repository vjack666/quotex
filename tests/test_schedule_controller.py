"""Unit tests for ScheduleController transitions."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from schedule_controller import ScheduleController


class FakeClock:
    def __init__(self, t: float = 1_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, sec: float) -> None:
        self.t += sec


class GateSleep:
    """Async sleep that parks until release(); advances clock on release."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.pending: list[tuple[float, asyncio.Future[None]]] = []

    async def __call__(self, sec: float) -> None:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[None] = loop.create_future()
        self.pending.append((sec, fut))
        await fut

    def release_one(self) -> float:
        if not self.pending:
            raise AssertionError("no pending sleep")
        sec, fut = self.pending.pop(0)
        self.clock.advance(sec)
        fut.set_result(None)
        return sec


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def _cfg(**over: object) -> dict:
    base = {
        "schedule_mode": "auto_full",
        "max_consecutive_sessions": 3,
        "work_block_hours": 2.0,
        "rest_hours": 1.0,
        "max_sessions_per_day": 0,
    }
    base.update(over)
    return base


def test_manual_mode_ignores_terminal(clock: FakeClock):
    sc = ScheduleController(clock=clock)
    sc.arm({"schedule_mode": "manual"})
    sc.on_user_start()
    assert sc.on_session_terminal({}) == "none"
    assert sc.phase == "idle"


def test_user_start_begins_work_block(clock: FakeClock):
    sc = ScheduleController(clock=clock)
    sc.arm(_cfg())
    sc.on_user_start()
    assert sc.phase == "working"
    assert sc.snapshot()["armed"] is True
    assert sc.snapshot()["mode"] == "auto_full"


def test_consecutive_sessions_enter_rest(clock: FakeClock):
    sc = ScheduleController(clock=clock)
    sc.arm(_cfg(max_consecutive_sessions=2, rest_hours=1.0))
    sc.on_user_start()
    assert sc.on_session_terminal({}) == "next_cycle"
    assert sc.consecutive == 1
    assert sc.phase == "working"
    assert sc.on_session_terminal({}) == "rest"
    assert sc.consecutive == 2
    assert sc.phase == "resting"
    snap = sc.snapshot()
    assert snap["rest_remaining_sec"] > 0
    assert snap["sessions_today"] == 2


@pytest.mark.asyncio
async def test_work_block_expiry_requests_stop(clock: FakeClock):
    stops: list[str] = []
    gate = GateSleep(clock)

    async def on_stop() -> None:
        stops.append("stop")

    sc = ScheduleController(
        clock=clock,
        on_request_stop=on_stop,
        sleep=gate,
    )
    sc.arm(_cfg(work_block_hours=2.0, rest_hours=0.5))
    sc.on_user_start()
    assert sc.phase == "working"
    await asyncio.sleep(0)  # let work monitor park on sleep
    assert gate.pending, "work monitor should be sleeping"
    sec = gate.release_one()
    assert abs(sec - 7200.0) < 0.1
    if sc._work_task:
        await sc._work_task
    assert "stop" in stops
    assert sc.phase == "resting"


@pytest.mark.asyncio
async def test_rest_then_auto_start(clock: FakeClock):
    starts: list[str] = []
    gate = GateSleep(clock)

    async def on_start() -> None:
        starts.append("start")

    sc = ScheduleController(
        clock=clock,
        on_request_start=on_start,
        sleep=gate,
    )
    sc.arm(_cfg(max_consecutive_sessions=1, rest_hours=1.0, work_block_hours=2.0))
    sc.on_user_start()
    await asyncio.sleep(0)  # work monitor parked
    assert sc.on_session_terminal({}) == "rest"
    assert sc.phase == "resting"
    await asyncio.sleep(0)  # rest monitor parked
    # pending: cancelled work may still be listed? work was cancelled so its fut may remain
    # Find rest sleep (~3600)
    rest_idx = next(i for i, (s, _) in enumerate(gate.pending) if abs(s - 3600.0) < 1)
    sec, fut = gate.pending.pop(rest_idx)
    clock.advance(sec)
    fut.set_result(None)
    if sc._rest_task:
        await sc._rest_task
    assert "start" in starts
    assert sc.phase == "working"
    assert sc.consecutive == 0


def test_user_stop_disarms(clock: FakeClock):
    sc = ScheduleController(clock=clock)
    sc.arm(_cfg())
    sc.on_user_start()
    assert sc.phase == "working"
    sc.on_user_stop()
    assert sc.phase == "disarmed"
    assert sc.snapshot()["armed"] is False
    assert sc.on_session_terminal({}) == "none"


def test_day_cap_blocks_auto(clock: FakeClock):
    sc = ScheduleController(clock=clock)
    sc.arm(_cfg(max_consecutive_sessions=10, max_sessions_per_day=2))
    sc.on_user_start()
    assert sc.on_session_terminal({}) == "next_cycle"
    assert sc.on_session_terminal({}) == "none"
    assert sc.sessions_today == 2
    assert sc.phase == "idle"


def test_snapshot_fields(clock: FakeClock):
    sc = ScheduleController(clock=clock)
    sc.arm(_cfg())
    sc.on_user_start()
    snap = sc.snapshot()
    assert snap["phase"] == "working"
    assert snap["work_block_remaining_sec"] == 7200
    assert "rest_remaining_sec" in snap
    assert "consecutive" in snap
    assert "max_consecutive" in snap
