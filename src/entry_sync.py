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
from core.models import EntryTimingInfo

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
        """Compute entry timing relative to the requested candle open."""
        # Preserve the existing implementation below this point.
        lag = max(0.0, float(now) - float(candle_open_ts))
        time_since_open_sec = lag
        ok = lag <= self.max_lag_sec and lag < self.reject_last_sec
        return EntryTimingInfo(
            ok=ok,
            lag_sec=lag,
            duration_sec=self.duration_sec,
            time_since_open_sec=time_since_open_sec,
        )
