"""Sincronización precisa de entradas con apertura de vela de entry TF."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import config as _cfg
from config import (
    ENTRY_MAX_LAG_SEC,
    ENTRY_REJECT_LAST_SEC,
    ENTRY_SYNC_TF_SEC,
    ENTRY_SYNC_TO_CANDLE,
)
from models import EntryTimingInfo

log = logging.getLogger("entry_sync")


class EntrySynchronizer:
    """Calcula y valida timing de entrada respecto al open de la vela de entry.

    Default TF is ``ENTRY_SYNC_TF_SEC`` (5m). Order placement waits for that
    candle open so buy/sell fire at the structure TF open, not 1m.

    ``duration_sec`` is an instance attribute. Callers that hot-reload config
    (hub → config.DURATION_SEC) MUST set ``self.duration_sec`` to the live
    value before ``sync_and_validate`` / ``compute_timing`` (TradeExecutor
    does this in ``_sync_to_next_candle_open``).
    """

    def __init__(
        self,
        *,
        tf_sec: int = ENTRY_SYNC_TF_SEC,
        max_lag_sec: float = ENTRY_MAX_LAG_SEC,
        reject_last_sec: float = ENTRY_REJECT_LAST_SEC,
        sync_enabled: bool = ENTRY_SYNC_TO_CANDLE,
        duration_sec: int | None = None,
        # Legacy alias — prefer tf_sec.
        tf_1m: int | None = None,
    ) -> None:
        if tf_1m is not None:
            tf_sec = int(tf_1m)
        self.tf_sec = int(tf_sec)
        # Back-compat alias used by older tests/callers.
        self.tf_1m = self.tf_sec
        self.max_lag_sec = float(max_lag_sec)
        self.reject_last_sec = float(reject_last_sec)
        self.sync_enabled = bool(sync_enabled)
        if duration_sec is None:
            duration_sec = int(getattr(_cfg, "DURATION_SEC", 300))
        self.duration_sec = int(duration_sec)

    def _next_candle_open(self, now: float) -> int:
        return ((int(now) // self.tf_sec) + 1) * self.tf_sec

    def compute_timing(self, candle_open_ts: int, now: float) -> EntryTimingInfo:
        """
        Evalúa timing puro respecto a un open de vela conocido.

        Args:
            candle_open_ts: timestamp Unix del open de la vela de entry.
            now: timestamp Unix actual (post-espera o instantáneo).
        """
        if not self.sync_enabled:
            return EntryTimingInfo(
                ok=True,
                lag_sec=0.0,
                duration_sec=self.duration_sec,
                time_since_open_sec=0.0,
                secs_to_close_sec=float(self.tf_sec),
                decision="SYNC_DISABLED",
            )

        lag_sec = max(0.0, now - float(candle_open_ts))
        time_since_open = now % self.tf_sec
        secs_to_close = max(0.0, self.tf_sec - time_since_open)

        if lag_sec > self.max_lag_sec or secs_to_close <= self.reject_last_sec:
            return EntryTimingInfo(
                ok=False,
                lag_sec=lag_sec,
                duration_sec=self.duration_sec,
                time_since_open_sec=time_since_open,
                secs_to_close_sec=secs_to_close,
                decision="REJECT_LATE_ENTRY",
            )

        return EntryTimingInfo(
            ok=True,
            lag_sec=lag_sec,
            duration_sec=self.duration_sec,
            time_since_open_sec=time_since_open,
            secs_to_close_sec=secs_to_close,
            decision="SYNCED_ENTRY_OPEN",
        )

    async def sync_and_validate(self, signal_ts: Optional[int] = None) -> EntryTimingInfo:
        """
        Espera al open de la vela de entry (o usa el actual si phase==0) y valida lag.
        """
        if not self.sync_enabled:
            return self.compute_timing(candle_open_ts=int(time.time()), now=time.time())

        now = time.time()
        phase = int(now) % self.tf_sec
        current_open = int(now) - phase
        if phase == 0:
            # Already at candle open — fire now, do not jump to next open.
            target_open = current_open
            wait_sec = 0.0
        else:
            target_open = current_open + self.tf_sec
            wait_sec = max(0.0, target_open - now)

        if wait_sec > 0:
            # Live TTY clock (same line); one durable log line inside helper.
            from loop_utils import sleep_with_inline_countdown

            await sleep_with_inline_countdown(
                wait_sec,
                f"Esperando open vela {self.tf_sec}s",
            )

        send_ts = time.time()
        timing = self.compute_timing(candle_open_ts=target_open, now=send_ts)

        if timing.ok:
            dur_min = timing.duration_sec // 60
            dur_seg = timing.duration_sec % 60
            log.info(
                "⏱ Entrada sincronizada al open de %ds: lag=%.2fs, restante=%.2fs "
                "→ duración fija=%dm%02ds (%ds)",
                self.tf_sec,
                timing.lag_sec,
                timing.secs_to_close_sec,
                dur_min,
                dur_seg,
                timing.duration_sec,
            )
        else:
            log.info(
                "⏳ Señal rechazada por timing %ds: lag=%.2fs, restante=%.2fs (max_lag=%.2fs)",
                self.tf_sec,
                timing.lag_sec,
                timing.secs_to_close_sec,
                self.max_lag_sec,
            )

        return timing

    def log_order_timing(self, asset: str, timing: EntryTimingInfo) -> None:
        """Telemetría por orden: time_since_open y secs_to_close."""
        log.info(
            "⏱ timing orden %s: time_since_open=%.3fs secs_to_close=%.3fs lag=%.3fs decision=%s",
            asset,
            timing.time_since_open_sec,
            timing.secs_to_close_sec,
            timing.lag_sec,
            timing.decision,
        )
