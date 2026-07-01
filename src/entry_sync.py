"""Sincronización precisa de entradas con apertura de vela 1m."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from config import (
    DURATION_SEC,
    ENTRY_MAX_LAG_SEC,
    ENTRY_REJECT_LAST_SEC,
    ENTRY_SYNC_TO_CANDLE,
    TF_1M,
)
from models import EntryTimingInfo

log = logging.getLogger("entry_sync")


class EntrySynchronizer:
    """Calcula y valida timing de entrada respecto al open de vela 1m."""

    def __init__(
        self,
        *,
        tf_1m: int = TF_1M,
        max_lag_sec: float = ENTRY_MAX_LAG_SEC,
        reject_last_sec: float = ENTRY_REJECT_LAST_SEC,
        sync_enabled: bool = ENTRY_SYNC_TO_CANDLE,
        duration_sec: int = DURATION_SEC,
    ) -> None:
        self.tf_1m = int(tf_1m)
        self.max_lag_sec = float(max_lag_sec)
        self.reject_last_sec = float(reject_last_sec)
        self.sync_enabled = bool(sync_enabled)
        self.duration_sec = int(duration_sec)

    @staticmethod
    def _next_candle_open(now: float) -> int:
        return ((int(now) // TF_1M) + 1) * TF_1M

    def compute_timing(self, candle_open_ts: int, now: float) -> EntryTimingInfo:
        """
        Evalúa timing puro respecto a un open de vela conocido.

        Args:
            candle_open_ts: timestamp Unix del open de vela 1m.
            now: timestamp Unix actual (post-espera o instantáneo).
        """
        if not self.sync_enabled:
            return EntryTimingInfo(
                ok=True,
                lag_sec=0.0,
                duration_sec=self.duration_sec,
                time_since_open_sec=0.0,
                secs_to_close_sec=float(self.tf_1m),
                decision="SYNC_DISABLED",
            )

        lag_sec = max(0.0, now - float(candle_open_ts))
        time_since_open = now % self.tf_1m
        secs_to_close = max(0.0, self.tf_1m - time_since_open)

        if lag_sec > self.max_lag_sec or secs_to_close <= self.reject_last_sec:
            return EntryTimingInfo(
                ok=False,
                lag_sec=lag_sec,
                duration_sec=self.duration_sec,
                time_since_open_sec=time_since_open,
                secs_to_close_sec=secs_to_close,
                decision="REJECT_LATE_1M",
            )

        return EntryTimingInfo(
            ok=True,
            lag_sec=lag_sec,
            duration_sec=self.duration_sec,
            time_since_open_sec=time_since_open,
            secs_to_close_sec=secs_to_close,
            decision="SYNCED_1M_OPEN",
        )

    async def sync_and_validate(self, signal_ts: Optional[int] = None) -> EntryTimingInfo:
        """
        Espera al próximo open de vela 1m y valida que el envío no llegue tarde.
        """
        if not self.sync_enabled:
            return self.compute_timing(candle_open_ts=int(time.time()), now=time.time())

        now = time.time()
        next_open = self._next_candle_open(now)
        wait_sec = max(0.0, next_open - now)
        if wait_sec > 0:
            log.info("⏳ Esperando apertura de vela 1m: %.2fs", wait_sec)
            await asyncio.sleep(wait_sec)

        send_ts = time.time()
        timing = self.compute_timing(candle_open_ts=next_open, now=send_ts)

        if timing.ok:
            dur_min = timing.duration_sec // 60
            dur_seg = timing.duration_sec % 60
            log.info(
                "⏱ Entrada sincronizada al open 1m: lag=%.2fs, restante=%.2fs → duración fija=%dm%02ds (%ds)",
                timing.lag_sec,
                timing.secs_to_close_sec,
                dur_min,
                dur_seg,
                timing.duration_sec,
            )
        else:
            log.info(
                "⏳ Señal rechazada por timing 1m: lag=%.2fs, restante=%.2fs (max_lag=%.2fs)",
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