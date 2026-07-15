"""Schedule controller for manual / auto_full overnight data collection.

Phases: idle | working | resting | disarmed

BotRunner supplies async callbacks for start/stop. The hub process stays
alive during rest; only the trading bot is stopped.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any, Awaitable, Callable

log = logging.getLogger(__name__)

StartCb = Callable[[], Awaitable[None]]
StopCb = Callable[[], Awaitable[None]]
ClockFn = Callable[[], float]
SleepFn = Callable[[float], Awaitable[None]]


class ScheduleController:
    """Work/rest/consecutive-session scheduler for schedule_mode=auto_full."""

    def __init__(
        self,
        *,
        clock: ClockFn | None = None,
        on_request_start: StartCb | None = None,
        on_request_stop: StopCb | None = None,
        sleep: SleepFn | None = None,
    ) -> None:
        self._clock: ClockFn = clock or time.time
        self._on_request_start = on_request_start
        self._on_request_stop = on_request_stop
        self._sleep: SleepFn = sleep or asyncio.sleep

        self.mode: str = "manual"
        self.phase: str = "idle"  # idle | working | resting | disarmed
        self.max_consecutive: int = 3
        self.work_block_hours: float = 2.0
        self.rest_hours: float = 1.0
        self.max_sessions_per_day: int = 0

        self.consecutive: int = 0
        self.sessions_today: int = 0
        self._day: date = date.fromtimestamp(self._clock())
        self.work_block_started_at: float | None = None
        self.rest_until: float | None = None
        self._armed: bool = False

        self._work_task: asyncio.Task[Any] | None = None
        self._rest_task: asyncio.Task[Any] | None = None
        self._next_task: asyncio.Task[Any] | None = None

    # ── config / arm ──────────────────────────────────────────────────────

    def configure(self, cfg: dict[str, Any]) -> None:
        self.mode = str(cfg.get("schedule_mode", "manual") or "manual")
        self.max_consecutive = max(1, int(cfg.get("max_consecutive_sessions", 3)))
        self.work_block_hours = max(0.1, float(cfg.get("work_block_hours", 2.0)))
        self.rest_hours = max(0.0, float(cfg.get("rest_hours", 1.0)))
        self.max_sessions_per_day = max(0, int(cfg.get("max_sessions_per_day", 0)))

    def arm(self, cfg: dict[str, Any] | None = None) -> None:
        """Prepare controller from config. Does not start a work block yet."""
        if cfg is not None:
            self.configure(cfg)
        if self.mode != "auto_full":
            self._armed = False
            self.phase = "idle"
            log.info("SCHEDULE mode=manual — not armed")
            return
        self._armed = True
        if self.phase == "disarmed":
            self.phase = "idle"
        log.info(
            "SCHEDULE armed mode=auto_full consec_max=%d work=%.1fh rest=%.1fh",
            self.max_consecutive,
            self.work_block_hours,
            self.rest_hours,
        )

    # ── lifecycle hooks ───────────────────────────────────────────────────

    def on_user_start(self) -> None:
        """User pressed Iniciar — arm work block if auto_full."""
        self._cancel_rest()
        self._cancel_next()
        if self.mode != "auto_full":
            self._armed = False
            self.phase = "idle"
            log.info("SCHEDULE user start mode=manual")
            return
        self._armed = True
        self.consecutive = 0
        self._begin_work_block()

    def on_user_stop(self) -> None:
        """User pressed Detener — cancel timers and disarm."""
        log.info("SCHEDULE user stop — disarmed")
        self._armed = False
        self.phase = "disarmed"
        self._cancel_work()
        self._cancel_rest()
        self._cancel_next()
        self.work_block_started_at = None
        self.rest_until = None

    def on_session_terminal(self, summary: dict[str, Any] | None = None) -> str:
        """Massaniello cycle finished. Returns action: none | next_cycle | rest."""
        del summary  # reserved for future logging
        self._roll_day()
        if not self._armed or self.mode != "auto_full":
            log.info("SCHEDULE session terminal ignored (not armed / manual)")
            return "none"

        self.consecutive += 1
        self.sessions_today += 1
        log.info(
            "SCHEDULE session terminal consecutive=%d/%d today=%d",
            self.consecutive,
            self.max_consecutive,
            self.sessions_today,
        )

        if self._day_cap_reached():
            log.info("SCHEDULE day cap reached — no auto restart")
            self.phase = "idle"
            self._cancel_work()
            return "none"

        if self.consecutive >= self.max_consecutive:
            log.info(
                "SCHEDULE max consecutive %d reached — rest %.1fh",
                self.max_consecutive,
                self.rest_hours,
            )
            self._enter_rest()
            return "rest"

        if self._work_expired():
            log.info("SCHEDULE work block expired at terminal — rest")
            self._enter_rest()
            return "rest"

        log.info(
            "SCHEDULE auto-start cycle %d/%d",
            self.consecutive + 1,
            self.max_consecutive,
        )
        self._schedule_next_start(delay=1.0)
        return "next_cycle"

    def snapshot(self) -> dict[str, Any]:
        now = self._clock()
        work_rem = 0.0
        if self.work_block_started_at is not None and self.phase == "working":
            elapsed = now - self.work_block_started_at
            work_rem = max(0.0, self.work_block_hours * 3600.0 - elapsed)
        rest_rem = 0.0
        if self.rest_until is not None and self.phase == "resting":
            rest_rem = max(0.0, self.rest_until - now)
        return {
            "mode": self.mode,
            "phase": self.phase,
            "armed": self._armed,
            "consecutive": self.consecutive,
            "max_consecutive": self.max_consecutive,
            "work_block_remaining_sec": int(work_rem),
            "rest_remaining_sec": int(rest_rem),
            "sessions_today": self.sessions_today,
            "max_sessions_per_day": self.max_sessions_per_day,
        }

    # ── internal ──────────────────────────────────────────────────────────

    def _begin_work_block(self) -> None:
        self.phase = "working"
        self.work_block_started_at = self._clock()
        self.rest_until = None
        log.info("SCHEDULE work block %.1fh", self.work_block_hours)
        self._cancel_work()
        self._spawn(self._work_monitor(), "schedule-work", kind="work")

    async def _work_monitor(self) -> None:
        wait = self.work_block_hours * 3600.0
        try:
            await self._sleep(wait)
        except asyncio.CancelledError:
            return
        if not self._armed or self.phase != "working":
            return
        log.info("SCHEDULE work block expired — stop")
        if self._on_request_stop is not None:
            try:
                await self._on_request_stop()
            except Exception as exc:
                log.warning("SCHEDULE request_stop failed: %s", exc)
        if self._armed and self.phase == "working":
            self._enter_rest()

    def _enter_rest(self) -> None:
        self._cancel_work()
        self._cancel_next()
        self.phase = "resting"
        self.rest_until = self._clock() + self.rest_hours * 3600.0
        log.info("SCHEDULE rest %.1fh", self.rest_hours)
        self._cancel_rest()
        if self.rest_hours <= 0:
            # Immediate resume path (tests / edge)
            self._spawn(self._rest_monitor(), "schedule-rest", kind="rest")
            return
        self._spawn(self._rest_monitor(), "schedule-rest", kind="rest")

    async def _rest_monitor(self) -> None:
        wait = max(0.0, (self.rest_until or self._clock()) - self._clock())
        try:
            await self._sleep(wait)
        except asyncio.CancelledError:
            return
        if not self._armed or self.phase != "resting":
            return
        self._roll_day()
        if self._day_cap_reached():
            log.info("SCHEDULE day cap after rest — stay idle")
            self.phase = "idle"
            self.rest_until = None
            return
        log.info("SCHEDULE rest ended — auto-start new work block")
        self.consecutive = 0
        self._begin_work_block()
        if self._on_request_start is not None:
            try:
                await self._on_request_start()
            except Exception as exc:
                log.warning("SCHEDULE request_start failed: %s", exc)

    def _schedule_next_start(self, delay: float = 1.0) -> None:
        async def _go() -> None:
            try:
                await self._sleep(delay)
            except asyncio.CancelledError:
                return
            if not self._armed or self.mode != "auto_full":
                return
            if self.phase not in ("working",):
                return
            if self._day_cap_reached():
                log.info("SCHEDULE day cap before next cycle")
                self.phase = "idle"
                return
            if self._work_expired():
                log.info("SCHEDULE work expired before next cycle — rest")
                self._enter_rest()
                return
            if self._on_request_start is not None:
                try:
                    await self._on_request_start()
                except Exception as exc:
                    log.warning("SCHEDULE next-cycle start failed: %s", exc)

        self._cancel_next()
        self._spawn(_go(), "schedule-next-cycle", kind="next")

    def _work_expired(self) -> bool:
        if self.work_block_started_at is None:
            return True
        return (self._clock() - self.work_block_started_at) >= self.work_block_hours * 3600.0

    def _day_cap_reached(self) -> bool:
        self._roll_day()
        if self.max_sessions_per_day <= 0:
            return False
        return self.sessions_today >= self.max_sessions_per_day

    def _roll_day(self) -> None:
        today = date.fromtimestamp(self._clock())
        if today != self._day:
            log.info("SCHEDULE day rollover — sessions_today reset")
            self._day = today
            self.sessions_today = 0

    def _spawn(
        self,
        coro: Awaitable[None],
        name: str,
        *,
        kind: str,
    ) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Pure unit tests without a loop — ignore background tasks
            return
        task = loop.create_task(coro, name=name)
        if kind == "work":
            self._work_task = task
        elif kind == "rest":
            self._rest_task = task
        else:
            self._next_task = task

    def _cancel_work(self) -> None:
        self._cancel_task("_work_task")

    def _cancel_rest(self) -> None:
        self._cancel_task("_rest_task")

    def _cancel_next(self) -> None:
        self._cancel_task("_next_task")

    def _cancel_task(self, attr: str) -> None:
        t: asyncio.Task[Any] | None = getattr(self, attr)
        setattr(self, attr, None)
        if t is None or t.done():
            return
        try:
            current = asyncio.current_task()
        except RuntimeError:
            current = None
        # Never cancel ourselves (e.g. work monitor entering rest)
        if t is not current:
            t.cancel()
